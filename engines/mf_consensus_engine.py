import numpy as np
import pandas as pd
from datetime import datetime
from sqlalchemy import func

from database.db import SessionLocal
from database.models import (
    MFScheme,
    MFPortfolioSnapshot,
    MFSchemeHolding,
    UserPortfolioHolding,
    Holding,
    StockMaster
)


class MFConsensusEngine:
    @classmethod
    def get_snapshots(cls) -> list[dict]:
        """Returns all available disclosure snapshots ordered chronologically descending."""
        db = SessionLocal()
        try:
            snaps = db.query(MFPortfolioSnapshot).order_by(MFPortfolioSnapshot.snapshot_date.desc()).all()
            return [
                {
                    "id": s.id,
                    "date": s.snapshot_date,
                    "month_str": s.month_str,
                    "source": s.source,
                    "total_schemes": s.total_schemes
                }
                for s in snaps
            ]
        finally:
            db.close()

    @classmethod
    def get_consensus_metrics(cls, snapshot_month: str = None, category_filter: str = "All", top_n_aum: int = None) -> pd.DataFrame:
        """
        Step 2: Consolidated Consensus Metrics Calculation.
        Calculates:
          - Confidence Score (Cs) = Number of schemes holding stock / Total active schemes in cohort
          - Average Across All Funds (Mean allocation across all schemes, including 0%)
          - Conviction Weight (Mean allocation among schemes actively holding the stock)
          - 3-tier hierarchy tags (Market Cap -> Sector -> Stock)
        """
        db = SessionLocal()
        try:
            # Determine snapshot date
            if not snapshot_month:
                latest_snap = db.query(MFPortfolioSnapshot).order_by(MFPortfolioSnapshot.snapshot_date.desc()).first()
                if not latest_snap:
                    return pd.DataFrame()
                target_date = latest_snap.snapshot_date
                month_label = latest_snap.month_str
            else:
                snap = db.query(MFPortfolioSnapshot).filter(MFPortfolioSnapshot.month_str == snapshot_month).first()
                if not snap:
                    return pd.DataFrame()
                target_date = snap.snapshot_date
                month_label = snap.month_str

            # Schemes query with optional category filter & AUM ranking
            scheme_query = db.query(MFScheme)
            if category_filter and category_filter not in ("All", "All Categories"):
                scheme_query = scheme_query.filter(MFScheme.category == category_filter)
            
            # Order schemes dynamically by AUM descending for cohort selection
            scheme_query = scheme_query.order_by(MFScheme.aum_cr.desc())
            if top_n_aum and top_n_aum > 0:
                scheme_query = scheme_query.limit(top_n_aum)

            schemes = scheme_query.all()
            total_schemes = len(schemes)
            if total_schemes == 0:
                return pd.DataFrame()

            scheme_ids = [s.id for s in schemes]
            scheme_category_map = {s.id: s.category for s in schemes}

            # Holdings query for this snapshot
            holdings = db.query(MFSchemeHolding).filter(
                MFSchemeHolding.snapshot_date == target_date,
                MFSchemeHolding.scheme_id.in_(scheme_ids)
            ).all()

            if not holdings:
                return pd.DataFrame()

            # Group holdings by ISIN / Stock
            stock_groups = {}
            for h in holdings:
                isin_key = h.isin or h.ticker
                if isin_key not in stock_groups:
                    stock_groups[isin_key] = {
                        "isin": h.isin,
                        "ticker": h.ticker,
                        "stock_name": h.stock_name,
                        "sector": h.sector or "Diversified",
                        "market_cap_category": h.market_cap_category or "Mid Cap",
                        "holding_schemes": set(),
                        "weights": [],
                        "category_breakdown": {}
                    }
                stock_groups[isin_key]["holding_schemes"].add(h.scheme_id)
                stock_groups[isin_key]["weights"].append(float(h.weight_pct or 0.0))

                s_cat = scheme_category_map.get(h.scheme_id, "Other")
                stock_groups[isin_key]["category_breakdown"].setdefault(s_cat, []).append(float(h.weight_pct or 0.0))

            # Category scheme counts
            category_scheme_counts = {}
            for s in schemes:
                category_scheme_counts[s.category] = category_scheme_counts.get(s.category, 0) + 1

            # Build consensus metrics table
            consensus_rows = []
            for isin_key, data in stock_groups.items():
                num_holding = len(data["holding_schemes"])
                confidence_score = round(num_holding / total_schemes, 4)
                confidence_pct = round(confidence_score * 100.0, 2)

                sum_weights = sum(data["weights"])
                avg_all_funds = round(sum_weights / total_schemes, 3)
                conviction_weight = round(sum_weights / num_holding, 3) if num_holding > 0 else 0.0

                # Category-specific peer confidence
                cat_conf_dict = {}
                for cat, total_in_cat in category_scheme_counts.items():
                    holding_in_cat = len([sid for sid in data["holding_schemes"] if scheme_category_map.get(sid) == cat])
                    cat_conf_dict[cat] = round((holding_in_cat / total_in_cat) * 100.0, 1) if total_in_cat > 0 else 0.0

                stock_cap_cat = data["market_cap_category"]
                primary_cat_conf = cat_conf_dict.get(stock_cap_cat, 0.0)
                max_peer_conf = max(cat_conf_dict.values()) if cat_conf_dict else confidence_pct
                effective_conf = max(confidence_pct, max_peer_conf)

                consensus_rows.append({
                    "ISIN": data["isin"],
                    "Ticker": data["ticker"],
                    "Stock Name": data["stock_name"],
                    "Market Cap Tier": data["market_cap_category"],
                    "Sector": data["sector"],
                    "Confidence Score": confidence_score,
                    "Confidence %": confidence_pct,
                    "Category Confidence %": primary_cat_conf,
                    "Peer Confidence %": effective_conf,
                    "Schemes Holding": num_holding,
                    "Total Schemes": total_schemes,
                    "Avg Weight All Funds %": avg_all_funds,
                    "Conviction Weight %": conviction_weight,
                    "Snapshot Month": month_label
                })

            df = pd.DataFrame(consensus_rows)
            if not df.empty:
                df = df.sort_values(by=["Peer Confidence %", "Avg Weight All Funds %"], ascending=[False, False])
            return df
        finally:
            db.close()

    @classmethod
    def get_temporal_deltas(cls, t0_month: str = None, t1_month: str = None, top_n_aum: int = None) -> pd.DataFrame:
        """
        Step 3: Delta Tracking Engine (Temporal Analysis).
        Compares selected month (T0) vs preceding month (T-1):
          - ΔW = Average Weight(T0) - Average Weight(T-1)
          - ΔC = Confidence(T0) - Confidence(T-1)
        Sentiment Rules:
          - Aggressive Accumulation: ΔW > +0.5% AND ΔC > +0.10
          - Modest Buying: ΔW > 0% AND ΔC >= 0
          - Profit Booking / Trimming: ΔW < 0% AND ΔC <= 0
          - Complete Exit: Confidence drops to 0 from previous > 0
        """
        snaps = cls.get_snapshots()
        if len(snaps) < 2:
            return pd.DataFrame()

        snap_months = [s["month_str"] for s in snaps]

        if not t0_month or t0_month not in snap_months:
            t0_month = snap_months[0]

        if not t1_month or t1_month not in snap_months:
            idx = snap_months.index(t0_month)
            if idx + 1 < len(snap_months):
                t1_month = snap_months[idx + 1]
            elif idx > 0:
                t1_month = snap_months[idx - 1]
            else:
                t1_month = snap_months[1]

        df_t0 = cls.get_consensus_metrics(snapshot_month=t0_month, top_n_aum=top_n_aum)
        df_t1 = cls.get_consensus_metrics(snapshot_month=t1_month, top_n_aum=top_n_aum)

        if df_t0.empty and df_t1.empty:
            return pd.DataFrame()

        # Merge on ISIN
        merged = pd.merge(
            df_t0,
            df_t1,
            on="ISIN",
            how="outer",
            suffixes=("_T0", "_T1")
        )

        merged["T0_Month"] = t0_month
        merged["T1_Month"] = t1_month

        # Fill metadata
        merged["Ticker"] = merged["Ticker_T0"].combine_first(merged["Ticker_T1"])
        merged["Stock Name"] = merged["Stock Name_T0"].combine_first(merged["Stock Name_T1"])
        merged["Sector"] = merged["Sector_T0"].combine_first(merged["Sector_T1"])
        merged["Market Cap Tier"] = merged["Market Cap Tier_T0"].combine_first(merged["Market Cap Tier_T1"])

        merged["Conf_T0"] = merged["Confidence Score_T0"].fillna(0.0)
        merged["Conf_T1"] = merged["Confidence Score_T1"].fillna(0.0)
        merged["Weight_T0"] = merged["Avg Weight All Funds %_T0"].fillna(0.0)
        merged["Weight_T1"] = merged["Avg Weight All Funds %_T1"].fillna(0.0)
        merged["Conviction_T0"] = merged["Conviction Weight %_T0"].fillna(0.0)
        merged["Conviction_T1"] = merged["Conviction Weight %_T1"].fillna(0.0)
        merged["Holding_Schemes_T0"] = merged["Schemes Holding_T0"].fillna(0).astype(int)
        merged["Holding_Schemes_T1"] = merged["Schemes Holding_T1"].fillna(0).astype(int)

        # Deltas
        merged["Delta_Weight"] = (merged["Weight_T0"] - merged["Weight_T1"]).round(3)
        merged["Delta_Confidence"] = (merged["Conf_T0"] - merged["Conf_T1"]).round(4)
        merged["Delta_Confidence_Pct"] = (merged["Delta_Confidence"] * 100.0).round(2)

        # Sentiment Classification
        def classify_sentiment(row):
            dw = row["Delta_Weight"]
            dc = row["Delta_Confidence"]
            c_t0 = row["Conf_T0"]
            c_t1 = row["Conf_T1"]

            if c_t1 > 0 and c_t0 == 0:
                return "Complete Exit", "🔴", -2
            if dw > 0.5 and dc > 0.10:
                return "Aggressive Accumulation", "🚀", 3
            if dw > 0 and dc >= 0:
                return "Modest Buying", "🟢", 1
            if dw < 0 and dc <= 0:
                return "Profit Booking / Trimming", "🟡", -1
            if dw > 0:
                return "Modest Buying", "🟢", 1
            if dw < 0:
                return "Profit Booking / Trimming", "🟡", -1
            return "Neutral", "⚪", 0

        classifications = [classify_sentiment(r) for _, r in merged.iterrows()]
        merged["Sentiment"] = [c[0] for c in classifications]
        merged["Sentiment_Icon"] = [c[1] for c in classifications]
        merged["Sentiment_Rank"] = [c[2] for c in classifications]

        out_cols = [
            "ISIN", "Ticker", "Stock Name", "Sector", "Market Cap Tier",
            "Weight_T0", "Weight_T1", "Delta_Weight",
            "Conf_T0", "Conf_T1", "Delta_Confidence", "Delta_Confidence_Pct",
            "Conviction_T0", "Conviction_T1",
            "Holding_Schemes_T0", "Holding_Schemes_T1",
            "Sentiment", "Sentiment_Icon", "Sentiment_Rank",
            "T0_Month", "T1_Month"
        ]
        return merged[out_cols].sort_values(by=["Delta_Weight", "Delta_Confidence"], ascending=[False, False])

    @classmethod
    def get_portfolio_gap_analysis(cls, snapshot_month: str = None, top_n_aum: int = None) -> dict:
        """
        Step 4: Personal Portfolio Gap & Misalignment Engine.
        Matches user portfolio against MF consensus using ISIN.
        Classifications:
          - Owned & Consensus Aligned: Held by user (> 0%) AND institutional confidence >= 30%
          - Institutional Misses (Gaps): Confidence >= 60% across top funds, but User Weight == 0%
          - Unbacked Bets: User Weight > 5%, but Institutional Confidence < 10%
          - Active Weight Diff = User Weight - MF Consensus Weight:
              * Overbought (Overweight): Active Weight Diff > +5.0%
              * Underbought (Underweight): Active Weight Diff < -3.0%
              * Aligned: between -3.0% and +5.0%
        """
        db = SessionLocal()
        try:
            # Query user portfolio
            user_items = db.query(UserPortfolioHolding).all()
            user_df = pd.DataFrame([
                {
                    "ISIN": u.isin,
                    "Ticker": u.ticker,
                    "Stock Name": u.stock_name,
                    "Holding Qty": u.holding_qty,
                    "User Weight %": u.current_weight_pct,
                    "Current Value": u.current_value
                }
                for u in user_items
            ])
        finally:
            db.close()

        consensus_df = cls.get_consensus_metrics(snapshot_month=snapshot_month, top_n_aum=top_n_aum)
        deltas_df = cls.get_temporal_deltas(t0_month=snapshot_month, top_n_aum=top_n_aum)

        if consensus_df.empty:
            return {
                "summary": {},
                "matched_df": pd.DataFrame(),
                "misses": pd.DataFrame(),
                "unbacked": pd.DataFrame(),
                "overweight": pd.DataFrame(),
                "underweight": pd.DataFrame(),
                "aligned": pd.DataFrame()
            }

        # Merge user with consensus
        if user_df.empty:
            user_df = pd.DataFrame(columns=["ISIN", "Ticker", "Stock Name", "Holding Qty", "User Weight %", "Current Value"])

        # Create comprehensive comparison frame
        full_df = pd.merge(
            consensus_df,
            user_df,
            on="ISIN",
            how="outer",
            suffixes=("_MF", "_User")
        )

        full_df["Ticker"] = full_df["Ticker_User"].combine_first(full_df["Ticker_MF"])
        full_df["Stock Name"] = full_df["Stock Name_User"].combine_first(full_df["Stock Name_MF"])
        full_df["User Weight %"] = full_df["User Weight %"].fillna(0.0)
        full_df["Holding Qty"] = full_df["Holding Qty"].fillna(0.0)
        full_df["Current Value"] = full_df["Current Value"].fillna(0.0)
        full_df["MF Consensus Weight %"] = full_df["Avg Weight All Funds %"].fillna(0.0)
        full_df["Confidence %"] = full_df["Confidence %"].fillna(0.0)
        full_df["Peer Confidence %"] = full_df["Peer Confidence %"].fillna(full_df["Confidence %"])
        full_df["Category Confidence %"] = full_df["Category Confidence %"].fillna(0.0)
        full_df["Conviction Weight %"] = full_df["Conviction Weight %"].fillna(0.0)
        full_df["Schemes Holding"] = full_df["Schemes Holding"].fillna(0).astype(int)
        full_df["Sector"] = full_df["Sector"].fillna("Other")
        full_df["Market Cap Tier"] = full_df["Market Cap Tier"].fillna("Mid Cap")

        # Merge delta sentiment info if available
        if not deltas_df.empty:
            delta_sub = deltas_df[["ISIN", "Delta_Weight", "Delta_Confidence_Pct", "Sentiment", "Sentiment_Icon"]]
            full_df = pd.merge(full_df, delta_sub, on="ISIN", how="left")
            full_df["Sentiment"] = full_df["Sentiment"].fillna("Neutral")
            full_df["Sentiment_Icon"] = full_df["Sentiment_Icon"].fillna("⚪")
            full_df["Delta_Weight"] = full_df["Delta_Weight"].fillna(0.0)
            full_df["Delta_Confidence_Pct"] = full_df["Delta_Confidence_Pct"].fillna(0.0)
        else:
            full_df["Sentiment"] = "Neutral"
            full_df["Sentiment_Icon"] = "⚪"
            full_df["Delta_Weight"] = 0.0
            full_df["Delta_Confidence_Pct"] = 0.0

        # Calculate Active Weight Diff
        full_df["Active Weight Diff"] = (full_df["User Weight %"] - full_df["MF Consensus Weight %"]).round(2)

        # Categorizations
        # 1. Institutional Misses: High confidence (>= 60% peer or >= 40% overall) across top funds, User Weight == 0%
        full_df["Effective_Confidence %"] = full_df[["Confidence %", "Peer Confidence %"]].max(axis=1)

        misses = full_df[
            (full_df["Effective_Confidence %"] >= 50.0) & (full_df["User Weight %"] <= 0.05)
        ].copy().sort_values(by=["Effective_Confidence %", "MF Consensus Weight %"], ascending=[False, False])

        # 2. Unbacked Bets: User Weight > 3%, Institutional Confidence < 15%
        unbacked = full_df[
            (full_df["User Weight %"] > 3.0) & (full_df["Confidence %"] < 15.0)
        ].copy().sort_values(by="User Weight %", ascending=False)

        # 3. Overbought / Underbought among owned stocks
        owned = full_df[full_df["User Weight %"] > 0.05].copy()

        overweight = owned[owned["Active Weight Diff"] > 5.0].copy().sort_values(by="Active Weight Diff", ascending=False)
        underweight = owned[owned["Active Weight Diff"] < -3.0].copy().sort_values(by="Active Weight Diff", ascending=True)
        aligned = owned[(owned["Active Weight Diff"] >= -3.0) & (owned["Active Weight Diff"] <= 5.0)].copy()

        # Status Labeling
        def assign_status(row):
            uw = row["User Weight %"]
            eff_conf = row["Effective_Confidence %"]
            diff = row["Active Weight Diff"]

            if uw <= 0.05 and eff_conf >= 50.0:
                return "Institutional Miss"
            if uw > 3.0 and row["Confidence %"] < 15.0:
                return "Unbacked Bet"
            if uw > 0.05:
                if diff > 5.0:
                    return "Overbought (Overweight)"
                if diff < -3.0:
                    return "Underbought (Underweight)"
                return "Consensus Aligned"
            return "Not Held (Low MF Conviction)"

        full_df["Ownership Category"] = full_df.apply(assign_status, axis=1)

        summary = {
            "total_user_stocks": len(owned),
            "total_institutional_misses": len(misses),
            "total_unbacked_bets": len(unbacked),
            "total_overweight": len(overweight),
            "total_underweight": len(underweight),
            "total_aligned": len(aligned)
        }

        return {
            "summary": summary,
            "matched_df": full_df,
            "misses": misses,
            "unbacked": unbacked,
            "overweight": overweight,
            "underweight": underweight,
            "aligned": aligned
        }

    @classmethod
    def get_next_best_actions(cls) -> list[dict]:
        """
        Step 5: Next Best Action & Recommendation Framework.
        Automated business rules:
          1. Buy Candidate: Confidence >= 60%, User Weight = 0%, Positive Delta C (or accumulating)
          2. Trim Candidate: User Weight > 15%, Fund Managers Delta W < -0.5% (or high overweight)
          3. Review Candidate: User Weight > 5%, Confidence < 5%
          4. Rebalance: User Sector Weight exceeds MF Sector Weight by > 15%
        """
        gap_data = cls.get_portfolio_gap_analysis()
        matched_df = gap_data.get("matched_df", pd.DataFrame())
        if matched_df.empty:
            return []

        actions = []

        # 1. Buy Candidates (Institutional Misses with accumulation)
        for _, r in matched_df.iterrows():
            eff_conf = float(r.get("Effective_Confidence %", r.get("Confidence %", 0.0)))
            if r["User Weight %"] <= 0.05 and eff_conf >= 50.0 and r["Delta_Weight"] >= 0.0:
                actions.append({
                    "type": "Buy Candidate",
                    "badge": "BUY",
                    "color": "#16a34a",
                    "priority": 1,
                    "ticker": r["Ticker"],
                    "stock_name": r["Stock Name"],
                    "sector": r["Sector"],
                    "reason": (
                        f"Consider initiating position in {r['Stock Name']}. "
                        f"{eff_conf:.0f}% of peer funds hold an average {r['Conviction Weight %']:.1f}% weight "
                        f"with active accumulation ({r['Delta_Weight']:+.2f}%) over the last month."
                    ),
                    "user_weight": r["User Weight %"],
                    "mf_weight": r["MF Consensus Weight %"],
                    "confidence": eff_conf,
                    "delta_weight": r["Delta_Weight"]
                })

        # 2. Trim Candidates (High concentration + fund managers trimming or overweight)
        for _, r in matched_df.iterrows():
            if r["User Weight %"] > 8.0 and (r["Delta_Weight"] < -0.2 or r["Active Weight Diff"] > 5.0):
                actions.append({
                    "type": "Trim Candidate",
                    "badge": "TRIM",
                    "color": "#eab308",
                    "priority": 2,
                    "ticker": r["Ticker"],
                    "stock_name": r["Stock Name"],
                    "sector": r["Sector"],
                    "reason": (
                        f"Reduce exposure in {r['Stock Name']}. You hold {r['User Weight %']:.1f}% vs "
                        f"MF average {r['MF Consensus Weight %']:.1f}%. Institutions have trimmed allocation "
                        f"({r['Delta_Weight']:+.2f}%) or you are heavily overweight."
                    ),
                    "user_weight": r["User Weight %"],
                    "mf_weight": r["MF Consensus Weight %"],
                    "confidence": r["Confidence %"],
                    "delta_weight": r["Delta_Weight"]
                })

        # 3. Review Candidates (Unbacked speculative stocks)
        for _, r in matched_df.iterrows():
            if r["User Weight %"] > 2.0 and r["Confidence %"] < 10.0:
                actions.append({
                    "type": "Review Candidate",
                    "badge": "REVIEW",
                    "color": "#ef4444",
                    "priority": 3,
                    "ticker": r["Ticker"],
                    "stock_name": r["Stock Name"],
                    "sector": r["Sector"],
                    "reason": (
                        f"Evaluate fundamental thesis for {r['Stock Name']}. You hold {r['User Weight %']:.1f}%, "
                        f"but fewer than {max(r['Confidence %'], 1.0):.0f}% of institutional equity funds hold this position."
                    ),
                    "user_weight": r["User Weight %"],
                    "mf_weight": r["MF Consensus Weight %"],
                    "confidence": r["Confidence %"],
                    "delta_weight": r["Delta_Weight"]
                })

        # 4. Sector Imbalance (User Sector Weight exceeds MF Sector Weight by > 10%)
        user_sectors = matched_df.groupby("Sector")["User Weight %"].sum()
        mf_sectors = matched_df.groupby("Sector")["MF Consensus Weight %"].sum()
        sector_diff = user_sectors - mf_sectors

        for sec, diff_val in sector_diff.items():
            if diff_val > 10.0:
                u_sec_wt = user_sectors.get(sec, 0.0)
                mf_sec_wt = mf_sectors.get(sec, 0.0)
                actions.append({
                    "type": "Sector Rebalance",
                    "badge": "REBALANCE",
                    "color": "#8b5cf6",
                    "priority": 4,
                    "ticker": sec,
                    "stock_name": f"{sec} Sector",
                    "sector": sec,
                    "reason": (
                        f"You are heavily overweight in {sec} ({u_sec_wt:.1f}% vs institutional average {mf_sec_wt:.1f}%). "
                        f"Consider reallocating capital into underweight institutional consensus sectors."
                    ),
                    "user_weight": u_sec_wt,
                    "mf_weight": mf_sec_wt,
                    "confidence": 100.0,
                    "delta_weight": 0.0
                })

        # Sort by priority
        actions = sorted(actions, key=lambda x: (x["priority"], -x["user_weight"]))
        return actions

    @classmethod
    def simulate_rebalance(
        cls,
        alignment_intensity: float = 0.5,
        stock_overrides: dict = None,
        capital_to_deploy: float = None,
        rebalance_mode: str = "self_funding",
        portfolio_id: str = "PORT001",
        snapshot_month: str = None,
        top_n_aum: int = None
    ) -> dict:
        """
        Step 6: Interactive Portfolio Rebalancing Simulator.
        Models convergence of user portfolio towards institutional consensus:
          New_Weight = (1 - intensity) * User_Weight + intensity * Target_Weight
        Calculates:
          - Herfindahl-Hirschman Index (HHI) concentration risk before vs after
          - Top 5 Holdings concentration % before vs after
          - Active Variance (Tracking Error proxy) reduction
          - Actionable Capital reallocation amounts (₹ Buy / ₹ Sell)
        """
        gap_data = cls.get_portfolio_gap_analysis(snapshot_month=snapshot_month, top_n_aum=top_n_aum)
        matched_df = gap_data.get("matched_df", pd.DataFrame())
        if matched_df.empty:
            return {}

        df = matched_df.copy()
        # Restrict to universe of user holdings + institutional misses + top institutional consensus
        active_universe = df[
            (df["User Weight %"] > 0) | 
            (df["Effective_Confidence %"] >= 50.0) | 
            (df["MF Consensus Weight %"] >= 2.0)
        ].copy()

        total_portfolio_value = df["Current Value"].sum()
        if total_portfolio_value <= 0:
            total_portfolio_value = 1000000.0  # Default ₹10 Lakhs simulation base

        # Normalize target MF weights within this active universe
        sum_mf_weights = active_universe["MF Consensus Weight %"].sum()
        if sum_mf_weights > 0:
            active_universe["Normalized_MF_Weight"] = (
                active_universe["MF Consensus Weight %"] / sum_mf_weights * 100.0
            ).round(2)
        else:
            active_universe["Normalized_MF_Weight"] = active_universe["MF Consensus Weight %"]

        # Calculate simulated weight
        alpha = float(alignment_intensity)  # 0.0 = 100% user, 1.0 = 100% MF target
        active_universe["Simulated_Weight %"] = (
            (1.0 - alpha) * active_universe["User Weight %"] + alpha * active_universe["Normalized_MF_Weight"]
        ).round(2)

        # Apply user overrides if any
        if stock_overrides:
            for isin, new_wt in stock_overrides.items():
                mask = active_universe["ISIN"] == isin
                if mask.any():
                    active_universe.loc[mask, "Simulated_Weight %"] = float(new_wt)

        # Re-normalize to 100%
        sim_sum = active_universe["Simulated_Weight %"].sum()
        if sim_sum > 0:
            active_universe["Simulated_Weight %"] = (
                active_universe["Simulated_Weight %"] / sim_sum * 100.0
            ).round(2)

        # Weight change and rupee shift
        active_universe["Weight Change (pp)"] = (
            active_universe["Simulated_Weight %"] - active_universe["User Weight %"]
        ).round(2)

        active_universe["Capital Shift ₹"] = (
            (active_universe["Weight Change (pp)"] / 100.0) * total_portfolio_value
        ).round(2)

        active_universe["Action"] = active_universe["Capital Shift ₹"].apply(
            lambda x: "BUY" if x > 500 else ("SELL" if x < -500 else "HOLD")
        )

        # LTP and Quantity mappings from active user portfolio and stock master
        db = SessionLocal()
        ltp_map = {}
        qty_map = {}
        try:
            for u in db.query(UserPortfolioHolding).all():
                if u.ticker:
                    tk_k = str(u.ticker).upper().strip()
                    curr_q = float(u.holding_qty or 0.0)
                    qty_map[tk_k] = curr_q
                    if curr_q > 0 and u.current_value and u.current_value > 0:
                        ltp_map[tk_k] = round(float(u.current_value) / curr_q, 2)

            for sm in db.query(StockMaster).all():
                if sm.ticker:
                    tk_k = str(sm.ticker).upper().strip()
                    if tk_k not in ltp_map and sm.close_price:
                        ltp_map[tk_k] = float(sm.close_price)
        finally:
            db.close()

        # Calculate baseline buy needs to determine minimum fresh capital required
        baseline_buy_needs = 0.0
        for _, row in active_universe.iterrows():
            ticker = str(row["Ticker"]).upper().strip()
            curr_qty = float(qty_map.get(ticker, row.get("Holding Qty", 0.0) or 0.0))
            ltp = float(ltp_map.get(ticker, 0.0))
            if ltp <= 0:
                ltp = 1000.0
            tgt_val = (float(row["Simulated_Weight %"]) / 100.0) * total_portfolio_value
            tgt_qty = round(tgt_val / ltp, 2)
            if tgt_qty > curr_qty:
                baseline_buy_needs += (tgt_qty - curr_qty) * ltp

        min_capital_for_zero_sell = round(baseline_buy_needs, 2)

        # Handle Capital Injection Modes
        injected_cash = float(capital_to_deploy or 0.0)
        is_fresh_injection = (rebalance_mode == "fresh_injection")
        is_hybrid = (rebalance_mode == "hybrid")

        effective_portfolio_base = total_portfolio_value
        if is_hybrid and injected_cash > 0:
            effective_portfolio_base = total_portfolio_value + injected_cash

        # Build trade orders dataframe
        trade_orders = []

        if is_fresh_injection:
            # PURE BUY MODE: No existing stock is ever sold!
            deployable_budget = injected_cash if injected_cash > 0 else min_capital_for_zero_sell

            # Identify underweighted and missing consensus stocks
            buy_candidates = []
            for _, row in active_universe.iterrows():
                ticker = str(row["Ticker"]).upper().strip()
                curr_qty = float(qty_map.get(ticker, row.get("Holding Qty", 0.0) or 0.0))
                ltp = float(ltp_map.get(ticker, 0.0))
                if ltp <= 0:
                    ltp = 1000.0
                curr_val = curr_qty * ltp
                target_mf_pct = float(row.get("Normalized_MF_Weight", row.get("Simulated_Weight %", 0.0)))
                buy_candidates.append({
                    "row": row,
                    "ticker": ticker,
                    "curr_qty": curr_qty,
                    "curr_val": curr_val,
                    "ltp": ltp,
                    "target_mf_pct": target_mf_pct
                })

            sum_target_pct = sum(c["target_mf_pct"] for c in buy_candidates if c["target_mf_pct"] > 0) or 100.0
            new_total_val = total_portfolio_value + deployable_budget

            for c in buy_candidates:
                ticker = c["ticker"]
                curr_qty = c["curr_qty"]
                ltp = c["ltp"]
                target_weight = round((c["target_mf_pct"] / sum_target_pct) * 100.0, 2)
                
                # Pro-rata cash allocation from fresh capital injection
                if c["target_mf_pct"] > 0:
                    stock_budget = (c["target_mf_pct"] / sum_target_pct) * deployable_budget
                    added_qty = round(stock_budget / ltp, 2)
                else:
                    added_qty = 0.0
                    stock_budget = 0.0

                if curr_qty <= 0.01 and added_qty > 0.01:
                    action = "BUY NEW"
                    qty_change = added_qty
                    trade_amt = round(-added_qty * ltp, 2)
                    target_qty = round(added_qty, 2)
                elif curr_qty > 0.01 and added_qty > 0.01:
                    action = "BUY MORE"
                    qty_change = added_qty
                    trade_amt = round(-added_qty * ltp, 2)
                    target_qty = round(curr_qty + added_qty, 2)
                else:
                    action = "HOLD"
                    qty_change = 0.0
                    target_qty = curr_qty
                    trade_amt = 0.0

                post_val = target_qty * ltp
                new_weight = round((post_val / new_total_val) * 100.0, 2) if new_total_val > 0 else target_weight

                trade_orders.append({
                    "Security": ticker,
                    "Stock Name": c["row"].get("Stock Name", ticker),
                    "Market Cap Tier": c["row"].get("Market Cap Tier", "Mid Cap"),
                    "Action": action,
                    "Current Qty": round(curr_qty, 2),
                    "Qty Change": round(qty_change, 2),
                    "Target Qty": round(target_qty, 2),
                    "LTP (₹)": round(ltp, 2),
                    "Trade Amount (₹)": trade_amt,
                    "Target Weight %": new_weight,
                    "Sector": c["row"].get("Sector", "Diversified"),
                    "User Weight %": round(float(c["row"].get("User Weight %", 0.0)), 2),
                    "Capital Shift ₹": trade_amt
                })

        else:
            # STANDARD / HYBRID REBALANCE MODE (Trimming + Buying)
            for _, row in active_universe.iterrows():
                ticker = str(row["Ticker"]).upper().strip()
                curr_qty = float(qty_map.get(ticker, row.get("Holding Qty", 0.0) or 0.0))
                
                ltp = float(ltp_map.get(ticker, 0.0))
                if ltp <= 0:
                    if curr_qty > 0 and row.get("Current Value", 0) > 0:
                        ltp = round(float(row["Current Value"]) / curr_qty, 2)
                    else:
                        ltp = 1000.0
                
                target_weight = float(row["Simulated_Weight %"])
                target_val = (target_weight / 100.0) * effective_portfolio_base
                target_qty = round(target_val / ltp, 2) if ltp > 0 else 0.0
                raw_qty_change = target_qty - curr_qty
                
                if curr_qty <= 0.01 and target_qty > 0.01:
                    action = "BUY NEW"
                    qty_change = round(target_qty, 2)
                    target_qty = round(curr_qty + qty_change, 2)
                    trade_amt = round(-qty_change * ltp, 2)
                elif raw_qty_change < -0.05:
                    if is_hybrid:
                        qty_change = round(raw_qty_change * 0.5, 2)
                        target_qty = round(curr_qty + qty_change, 2)
                        action = "TRIM"
                        trade_amt = round(abs(qty_change) * ltp, 2)
                    else:
                        qty_change = round(raw_qty_change, 2)
                        target_qty = round(max(0.0, curr_qty + qty_change), 2)
                        action = "TRIM" if target_qty > 0.01 else "SELL ALL"
                        trade_amt = round(abs(qty_change) * ltp, 2)
                elif raw_qty_change > 0.05 and curr_qty > 0.01:
                    action = "BUY MORE"
                    qty_change = round(raw_qty_change, 2)
                    target_qty = round(curr_qty + qty_change, 2)
                    trade_amt = round(-qty_change * ltp, 2)
                else:
                    action = "HOLD"
                    qty_change = 0.0
                    target_qty = curr_qty
                    trade_amt = 0.0
                
                trade_orders.append({
                    "Security": ticker,
                    "Stock Name": row.get("Stock Name", ticker),
                    "Market Cap Tier": row.get("Market Cap Tier", "Mid Cap"),
                    "Action": action,
                    "Current Qty": round(curr_qty, 2),
                    "Qty Change": round(qty_change, 2),
                    "Target Qty": round(target_qty, 2),
                    "LTP (₹)": round(ltp, 2),
                    "Trade Amount (₹)": trade_amt,
                    "Target Weight %": round(target_weight, 2),
                    "Sector": row.get("Sector", "Diversified"),
                    "User Weight %": round(float(row.get("User Weight %", 0.0)), 2),
                    "Capital Shift ₹": round(float(row.get("Capital Shift ₹", 0.0)), 2)
                })

        orders_df = pd.DataFrame(trade_orders)
        if not orders_df.empty:
            action_order = {
                "BUY NEW": 1, "BUY MORE": 2, "HOLD": 3, "TRIM": 4, "SELL ALL": 5, "SELL": 5
            } if is_fresh_injection else {
                "TRIM": 1, "SELL ALL": 2, "SELL": 2, "BUY MORE": 3, "BUY NEW": 4, "HOLD": 5
            }
            orders_df["_sort_key"] = orders_df["Action"].map(action_order).fillna(6)
            orders_df = orders_df.sort_values(
                by=["_sort_key", "Trade Amount (₹)", "Target Weight %"],
                ascending=[True, False, False]
            ).drop(columns=["_sort_key"])

        # Risk metrics calculation:
        # 1. Concentration: Herfindahl-Hirschman Index (HHI = sum(w^2))
        w_orig = active_universe["User Weight %"].values
        w_sim = active_universe["Simulated_Weight %"].values

        hhi_before = float(np.sum(w_orig ** 2))
        hhi_after = float(np.sum(w_sim ** 2))
        hhi_reduction_pct = round(((hhi_before - hhi_after) / max(hhi_before, 1)) * 100.0, 1)

        # 2. Top 5 Holdings concentration
        top5_before = float(np.sum(np.sort(w_orig)[::-1][:5]))
        top5_after = float(np.sum(np.sort(w_sim)[::-1][:5]))

        # 3. Active Variance proxy (sum of squared deviations from consensus)
        w_mf = active_universe["Normalized_MF_Weight"].values
        active_var_before = float(np.sum((w_orig - w_mf) ** 2))
        active_var_after = float(np.sum((w_sim - w_mf) ** 2))
        variance_reduction_pct = round(((active_var_before - active_var_after) / max(active_var_before, 1)) * 100.0, 1)

        # Capital metrics calculation:
        total_trim_freed = sum(
            o["Trade Amount (₹)"] for o in trade_orders if o["Action"] in ("TRIM", "SELL", "SELL ALL")
        )
        total_buy_required = sum(
            abs(o["Trade Amount (₹)"]) for o in trade_orders if o["Action"] in ("BUY", "BUY NEW", "BUY MORE")
        )
        net_cash_needed = max(0.0, round(total_buy_required - total_trim_freed, 2))
        effective_portfolio_base = round(total_portfolio_value + net_cash_needed, 2)

        return {
            "simulated_df": active_universe.sort_values(by="Simulated_Weight %", ascending=False),
            "trade_orders_df": orders_df,
            "total_portfolio_value": total_portfolio_value,
            "effective_portfolio_base": effective_portfolio_base,
            "min_capital_for_zero_sell": min_capital_for_zero_sell,
            "total_trim_freed": round(total_trim_freed, 2),
            "total_buy_required": round(total_buy_required, 2),
            "net_cash_needed": round(net_cash_needed, 2),
            "fresh_cash_needed": round(net_cash_needed, 2),
            "rebalance_mode": rebalance_mode,
            "capital_injected": round(net_cash_needed, 2),
            "hhi_before": round(hhi_before, 0),
            "hhi_after": round(hhi_after, 0),
            "hhi_reduction_pct": hhi_reduction_pct,
            "top5_before": round(top5_before, 1),
            "top5_after": round(top5_after, 1),
            "active_var_before": round(active_var_before, 0),
            "active_var_after": round(active_var_after, 0),
            "variance_reduction_pct": variance_reduction_pct,
            "total_buy_inr": round(total_buy_required, 2),
            "total_sell_inr": round(total_trim_freed, 2),
            "top_n_aum": top_n_aum
        }
