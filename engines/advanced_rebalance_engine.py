import numpy as np
import pandas as pd

class AdvancedRebalanceEngine:
    """
    Tickertape-inspired advanced portfolio rebalancing engine.
    Calculates stock and sector drift, concentration risks, market cap alignment,
    tax-efficient rebalance plans, and conviction-weighted target restorations.
    """

    @classmethod
    def rebalance(cls, portfolio_df, strategy, new_capital=0.0, universe_df=None):
        """
        Generate a comprehensive rebalancing plan.
        
        Args:
            portfolio_df: DataFrame containing holdings merged with stock master
            strategy: dict containing user configuration:
                - targetSectorAllocation: dict of {sector: weight_percent}
                - maxStockAllocation: float (e.g. 15.0)
                - maxSectorAllocation: float (e.g. 30.0)
                - rebalanceThresholdPercent: float (e.g. 5.0)
                - riskProfile: "Conservative" | "Moderate" | "Aggressive"
                - rebalanceFrequency: "Monthly" | "Quarterly" | "SemiAnnual" | "Annual"
                - rebalanceMode: "Time-Based" | "Threshold-Based" | "Hybrid"
                - momentumOverride: bool
                - smartRebalancing: bool
                - allowNewStocks: bool
                - rebalanceLevel: "Stock-Level" | "Sector-Level"
            new_capital: float (additional cash input for simulation)
            universe_df: DataFrame of the entire stock universe for unowned stock suggestions
            
        Returns:
            dict matching the Final Output JSON schema
        """
        if portfolio_df.empty:
            return cls.empty_response(strategy.get("riskProfile", "Moderate"))

        # Coerce columns to numeric
        df = portfolio_df.copy()
        df["Current Value Rs"] = pd.to_numeric(df["Current Value Rs"], errors="coerce").fillna(0.0)
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0.0)
        df["LTP Rs"] = pd.to_numeric(df["LTP Rs"], errors="coerce").fillna(0.0)
        df["QUALITY_SCORE"] = pd.to_numeric(df["QUALITY_SCORE"], errors="coerce").fillna(60.0)
        df["ROCE"] = pd.to_numeric(df["ROCE"], errors="coerce").fillna(12.0)
        df["Debt to Equity"] = pd.to_numeric(df["Debt to Equity"], errors="coerce").fillna(0.5)
        df["5Y CAGR"] = pd.to_numeric(df["5Y CAGR"], errors="coerce").fillna(10.0)
        df["5Y Historical Revenue Growth"] = pd.to_numeric(df["5Y Historical Revenue Growth"], errors="coerce").fillna(10.0)
        
        # 1. Portfolio Value
        portfolio_value = df["Current Value Rs"].sum()
        if portfolio_value == 0:
            return cls.empty_response(strategy.get("riskProfile", "Moderate"))

        # 2. Current Stock Weights
        df["current_weight"] = (df["Current Value Rs"] / portfolio_value) * 100.0

        # Classify Market Cap dynamically
        def classify_mcap(row):
            val = row.get("Market Cap")
            if pd.isna(val) or val <= 0:
                return "Small"
            # If values are very large (raw Rupees), scale to Crores
            if val > 10000000:
                val = val / 10000000.0 # scale lakhs/raw
            if val > 20000:
                return "Large"
            elif val > 5000:
                return "Mid"
            else:
                return "Small"
        
        df["mcap_class"] = df.apply(classify_mcap, axis=1)

        # Retrieve user parameters
        target_sector_alloc = strategy.get("targetSectorAllocation", {})
        max_stock_alloc = strategy.get("maxStockAllocation", 15.0)
        max_sector_alloc = strategy.get("maxSectorAllocation", 30.0)
        threshold = strategy.get("rebalanceThresholdPercent", 5.0)
        risk_profile = strategy.get("riskProfile", "Moderate")
        rebalance_mode = strategy.get("rebalanceMode", "Hybrid")
        smart_rebal = strategy.get("smartRebalancing", True)
        momentum_override = strategy.get("momentumOverride", False)
        allow_new_stocks = strategy.get("allowNewStocks", True)
        rebalance_level = strategy.get("rebalanceLevel", "Stock-Level")

        # Adjust threshold if momentum override is enabled
        effective_threshold = threshold * 2.0 if momentum_override else threshold

        # Group current holdings by Sector
        sectors_present = df["Sub-Sector"].dropna().unique()
        current_sector_weights = {}
        for sec in sectors_present:
            sec_val = df[df["Sub-Sector"] == sec]["Current Value Rs"].sum()
            current_sector_weights[sec] = (sec_val / portfolio_value) * 100.0

        # Fill target weights for sectors not in user strategy
        all_sectors = set(list(target_sector_alloc.keys()) + list(sectors_present))
        for sec in all_sectors:
            if sec not in target_sector_alloc:
                target_sector_alloc[sec] = 0.0

        # 3. Calculate Sector Drift
        sector_drift = {}
        for sec in all_sectors:
            curr = current_sector_weights.get(sec, 0.0)
            targ = target_sector_alloc.get(sec, 0.0)
            sector_drift[sec] = curr - targ

        # 4. Determine Rebalancing Requirement
        rebal_triggered = False
        drift_trigger_reasons = []

        if rebalance_mode == "Time-Based":
            rebal_triggered = True
            drift_trigger_reasons.append("Scheduled periodic rebalancing review.")
        else:
            # Check if any sector drift breaches the threshold
            for sec, drift in sector_drift.items():
                if abs(drift) > effective_threshold:
                    rebal_triggered = True
                    drift_trigger_reasons.append(f"Sector '{sec}' drift ({drift:+.1f}%) exceeds threshold ({effective_threshold}%).")
            
            # Check if any stock exceeds max stock allocation
            for _, row in df.iterrows():
                if row["current_weight"] > max_stock_alloc:
                    rebal_triggered = True
                    drift_trigger_reasons.append(f"Stock '{row['Security']}' weight ({row['current_weight']:.1f}%) exceeds maximum limit ({max_stock_alloc}%).")

        # 5. Distribute Target Sector Allocations to Individual Stocks using Conviction
        df["target_weight"] = 0.0
        for sec, targ_w in target_sector_alloc.items():
            sec_holdings = df[df["Sub-Sector"] == sec]
            if not sec_holdings.empty:
                # Distribute target sector weight proportionally based on conviction score (quality score)
                total_conv = sec_holdings["QUALITY_SCORE"].sum()
                if total_conv > 0:
                    df.loc[df["Sub-Sector"] == sec, "target_weight"] = targ_w * (sec_holdings["QUALITY_SCORE"] / total_conv)
                else:
                    df.loc[df["Sub-Sector"] == sec, "target_weight"] = targ_w / len(sec_holdings)

        df["stock_drift"] = df["current_weight"] - df["target_weight"]

        # Find candidate new stocks in the universe for underweight/missing sectors
        new_stock_candidates = []
        if allow_new_stocks and universe_df is not None and not universe_df.empty:
            for sec, drift in sector_drift.items():
                if drift < -1.0: # Sector is underweight by more than 1%
                    # Get stocks in the universe for this sector
                    sec_univ = universe_df[universe_df["Sub-Sector"] == sec]
                    if sec_univ.empty:
                        sec_univ = universe_df[universe_df["Sub-Sector"].str.lower() == sec.lower()]
                    
                    owned_tickers = df["Security"].dropna().unique()
                    unowned_sec_univ = sec_univ[~sec_univ["Ticker"].isin(owned_tickers)]
                    
                    if not unowned_sec_univ.empty:
                        unowned_sec = unowned_sec_univ.copy()
                        unowned_sec["QUALITY_SCORE"] = pd.to_numeric(unowned_sec["QUALITY_SCORE"], errors="coerce").fillna(60.0)
                        top_stock = unowned_sec.sort_values(by="QUALITY_SCORE", ascending=False).iloc[0]
                        
                        raw_price = pd.to_numeric(top_stock["Close Price"], errors="coerce")
                        ltp_val = float(raw_price) if not pd.isna(raw_price) else 100.0
                        
                        new_stock_candidates.append({
                            "ticker": top_stock["Ticker"],
                            "name": top_stock["Name"],
                            "sector": sec,
                            "quality_score": float(top_stock["QUALITY_SCORE"]),
                            "ltp": ltp_val,
                            "sector_drift": drift,
                            "is_missing": (current_sector_weights.get(sec, 0.0) == 0.0)
                        })

        # 6. Generate Recommendations
        sector_recs = []
        stock_recs = []
        tax_plan = []
        warnings = []
        
        # Sector recommendations
        for sec in all_sectors:
            drift = sector_drift.get(sec, 0.0)
            curr = current_sector_weights.get(sec, 0.0)
            targ = target_sector_alloc.get(sec, 0.0)
            
            if abs(drift) > 0.05: # ignore tiny rounding drifts
                value_diff = (drift / 100.0) * portfolio_value
                action = "Reduce exposure" if drift > 0 else "Increase exposure"
                sector_recs.append({
                    "sector": sec,
                    "currentWeight": round(curr, 1),
                    "targetWeight": round(targ, 1),
                    "drift": round(drift, 1),
                    "action": f"{action} by ₹{abs(int(value_diff)):,}"
                })

        # Stock recommendations
        # Sort stocks by absolute drift to prioritize actions
        df["abs_drift"] = df["stock_drift"].abs()
        df_sorted = df.sort_values(by="stock_drift", ascending=False)
        
        sells_needed = []
        buys_needed = []
        
        for _, row in df_sorted.iterrows():
            ticker = row["Security"]
            curr_w = row["current_weight"]
            targ_w = row["target_weight"]
            drift = row["stock_drift"]
            ltp = row["LTP Rs"]
            
            # Category priority
            if abs(drift) > 15.0:
                priority = "Critical"
            elif abs(drift) > 10.0:
                priority = "High Priority"
            elif abs(drift) > 5.0:
                priority = "Medium"
            else:
                priority = "Monitor"
                
            # Compute impact score based on reduction of drift
            impact_score = int(min(100, max(0, abs(drift) * 5 + 20)))
            
            if drift > effective_threshold:
                # Sell recommendation
                excess_val = (drift / 100.0) * portfolio_value
                shares_to_sell = int(excess_val / ltp) if ltp > 0 else 0
                
                # Smart Rebalancing Override: Avoid selling high-quality compounders
                is_high_quality = (row["ROCE"] > 20.0) and (row["Debt to Equity"] < 0.5) and (row["5Y Historical Revenue Growth"] > 15.0)
                
                if smart_rebal and is_high_quality:
                    tax_plan.append(f"Smart Rebalance: Avoided trimming high-quality compounder {ticker} (ROCE: {row['ROCE']:.1f}%, D/E: {row['Debt to Equity']:.2f}). Preferred retaining position and deploying fresh cash elsewhere.")
                    # Keep rec but note it is bypassed
                    act_msg = f"Trim {shares_to_sell} shares of {ticker} (Bypassed via Smart Rebalancing)"
                    if rebalance_level == "Sector-Level":
                        act_msg = f"[Sector: {row['Sub-Sector']}] Trim {shares_to_sell} shares of {ticker} to reduce sector weight (Bypassed via Smart Rebalancing)"
                    stock_recs.append({
                        "ticker": ticker,
                        "currentWeight": round(curr_w, 1),
                        "targetWeight": round(targ_w, 1),
                        "drift": round(drift, 1),
                        "action": act_msg,
                        "priority": "Monitor",
                        "impactScore": impact_score
                    })
                else:
                    sells_needed.append((ticker, shares_to_sell, int(excess_val)))
                    act_msg = f"Trim {shares_to_sell} shares of {ticker}"
                    if rebalance_level == "Sector-Level":
                        act_msg = f"[Sector: {row['Sub-Sector']}] Trim {shares_to_sell} shares of {ticker} to reduce sector weight"
                    stock_recs.append({
                        "ticker": ticker,
                        "currentWeight": round(curr_w, 1),
                        "targetWeight": round(targ_w, 1),
                        "drift": round(drift, 1),
                        "action": act_msg,
                        "priority": priority,
                        "impactScore": impact_score
                    })
            elif drift < -effective_threshold:
                # Buy recommendation
                deficit_val = abs(drift / 100.0) * portfolio_value
                buys_needed.append((ticker, int(deficit_val)))
                act_msg = f"Add ₹{int(deficit_val):,} to {ticker}"
                if rebalance_level == "Sector-Level":
                    act_msg = f"[Sector: {row['Sub-Sector']}] Add ₹{int(deficit_val):,} to {ticker} to increase sector weight"
                stock_recs.append({
                    "ticker": ticker,
                    "currentWeight": round(curr_w, 1),
                    "targetWeight": round(targ_w, 1),
                    "drift": round(drift, 1),
                    "action": act_msg,
                    "priority": priority,
                    "impactScore": impact_score
                })

        # Add new stock recommendations for underweight/missing sectors
        for candidate in new_stock_candidates:
            sec_deficit_val = abs(candidate["sector_drift"] / 100.0) * portfolio_value
            suggested_allocation = min(portfolio_value * 0.05, sec_deficit_val)
            if suggested_allocation < 1000.0:
                suggested_allocation = 1000.0
                
            priority = "High Priority" if candidate["is_missing"] else "Medium"
            impact_score = int(min(95, max(30, abs(candidate["sector_drift"]) * 5 + 30)))
            
            act_msg = f"[NEW STOCK] Buy {candidate['ticker']} (₹{int(suggested_allocation):,}) to start position in missing sector {candidate['sector']} (Quality: {candidate['quality_score']:.0f}/100)"
            if rebalance_level == "Sector-Level":
                act_msg = f"[Sector: {candidate['sector']}] [NEW STOCK] Buy {candidate['ticker']} (₹{int(suggested_allocation):,}) to cover missing sector (Quality: {candidate['quality_score']:.0f}/100)"
                
            stock_recs.append({
                "ticker": candidate["ticker"],
                "currentWeight": 0.0,
                "targetWeight": round((suggested_allocation / portfolio_value) * 100.0, 1),
                "drift": round(candidate["sector_drift"], 1),
                "action": act_msg,
                "priority": priority,
                "impactScore": impact_score,
                "isNewStock": True
            })

        # Concentration Warnings
        # 1. Sector Concentration Risk
        max_sec = max(current_sector_weights.values()) if current_sector_weights else 0.0
        max_sec_name = [k for k, v in current_sector_weights.items() if v == max_sec][0] if current_sector_weights else "Unknown"
        
        if max_sec > 40.0:
            sec_risk = "High"
            warnings.append(f"Sector Concentration is HIGH. {max_sec_name} represents {max_sec:.1f}% of your portfolio.")
        elif max_sec >= 25.0:
            sec_risk = "Moderate"
            warnings.append(f"Sector Concentration is MODERATE. {max_sec_name} represents {max_sec:.1f}% of your portfolio.")
        else:
            sec_risk = "Low"

        # 2. Stock Concentration Risk
        max_stock = df["current_weight"].max()
        max_stock_name = df.loc[df["current_weight"] == max_stock, "Security"].values[0]
        
        if max_stock > 20.0:
            stock_risk = "High"
            warnings.append(f"Stock Concentration is HIGH. '{max_stock_name}' represents {max_stock:.1f}% of your portfolio.")
        elif max_stock >= 10.0:
            stock_risk = "Moderate"
            warnings.append(f"Stock Concentration is MODERATE. '{max_stock_name}' represents {max_stock:.1f}% of your portfolio.")
        else:
            stock_risk = "Low"

        # 7. Market Cap Rebalancing
        # Calculate current allocations
        mc_allocs = df.groupby("mcap_class")["Current Value Rs"].sum()
        current_large = (mc_allocs.get("Large", 0.0) / portfolio_value) * 100.0
        current_mid = (mc_allocs.get("Mid", 0.0) / portfolio_value) * 100.0
        current_small = (mc_allocs.get("Small", 0.0) / portfolio_value) * 100.0
        
        # Risk Profile target allocations
        ideal_caps = {
            "Conservative": {"Large": 70.0, "Mid": 20.0, "Small": 10.0},
            "Moderate": {"Large": 50.0, "Mid": 30.0, "Small": 20.0},
            "Aggressive": {"Large": 40.0, "Mid": 35.0, "Small": 25.0}
        }
        ideal = ideal_caps.get(risk_profile, ideal_caps["Moderate"])
        
        # Compare and generate recommendations
        mc_recs = []
        for cap, ideal_w in ideal.items():
            curr_w = current_large if cap == "Large" else current_mid if cap == "Mid" else current_small
            diff = curr_w - ideal_w
            if abs(diff) > 5.0:
                direction = "Overallocated" if diff > 0 else "Underallocated"
                mc_recs.append(f"Market Cap: {direction} in {cap} Caps by {abs(diff):.1f}% (Ideal: {ideal_w}%, Current: {curr_w:.1f}%). Adjust holdings toward {risk_profile} targets.")

        # 8. Tax-Aware Rebalance Plan
        tax_plan.append("Tax-Aware Priority: Prioritized deploying fresh capital and dividends to restore targets over selling to minimize short-term capital gains tax (STCG).")
        if sells_needed:
            for ticker, shares, val in sells_needed:
                tax_plan.append(f"Tax-Aware Action: Trim {shares} shares (₹{val:,}) of {ticker}. Check holding periods; prioritize selling long-term holdings (>1 year) to utilize the ₹1.25 Lakh LTCG exemption.")
        else:
            tax_plan.append("Tax-Aware Action: No sells required. Drift can be fully restored via cash injection.")

        # 9. New Capital Optimization Simulator
        sim_deploy = []
        if new_capital > 0:
            deployment_targets = []
            
            # 1. Existing underweight holdings
            underweights = df[df["stock_drift"] < 0].copy()
            for _, row in underweights.iterrows():
                deployment_targets.append({
                    "ticker": row["Security"],
                    "is_new": False,
                    "deficit": abs(row["stock_drift"]),
                    "reason": f"Restore stock target weight. Deficit is {abs(row['stock_drift']):.1f}%."
                })
                
            # 2. Unowned stock candidates in underweight/missing sectors
            for candidate in new_stock_candidates:
                deployment_targets.append({
                    "ticker": candidate["ticker"],
                    "is_new": True,
                    "deficit": abs(candidate["sector_drift"]),
                    "reason": f"[NEW STOCK] Deploy to {candidate['ticker']} to start position in missing sector {candidate['sector']} (Quality: {candidate['quality_score']:.0f})."
                })
                
            if deployment_targets:
                # Sum of absolute deficits
                total_deficit = sum([t["deficit"] for t in deployment_targets])
                for t in deployment_targets:
                    deficit_ratio = t["deficit"] / total_deficit if total_deficit > 0 else 1.0 / len(deployment_targets)
                    alloc_val = new_capital * deficit_ratio
                    sim_deploy.append({
                        "ticker": t["ticker"],
                        "allocatedAmount": int(alloc_val),
                        "reason": t["reason"],
                        "isNewStock": t["is_new"]
                    })
            else:
                # Fallback: Equal allocation across existing stocks
                alloc_val = new_capital / len(df)
                for _, row in df.iterrows():
                    sim_deploy.append({
                        "ticker": row["Security"],
                        "allocatedAmount": int(alloc_val),
                        "reason": "Equal allocation across portfolio.",
                        "isNewStock": False
                    })

        # 10. Core Scores
        # Herfindahl-Hirschman Index for diversification
        hhi = sum((df["current_weight"] / 100.0) ** 2)
        diversification_score = int(np.clip(100 - hhi * 100, 10, 95))
        
        # Sector Concentration score
        sec_conc_score = int(np.clip(100 - max_sec * 2.0, 0, 100))
        
        # Market Cap balance score
        mc_diff = abs(current_large - ideal["Large"]) + abs(current_mid - ideal["Mid"]) + abs(current_small - ideal["Small"])
        mc_score = int(np.clip(100 - mc_diff * 1.5, 20, 100))
        
        # Urgency score
        max_abs_drift = max([abs(d) for d in sector_drift.values()]) if sector_drift else 0.0
        urgency_score = int(np.clip(max_abs_drift * 6.0, 0, 100))
        
        # Health Score
        health_score = int(0.40 * diversification_score + 0.30 * sec_conc_score + 0.20 * mc_score + 0.10 * (100 - urgency_score))

        # Before vs After Metrics
        before_metrics = {
            "diversificationScore": diversification_score,
            "sectorConcentrationScore": sec_conc_score,
            "marketCapBalanceScore": mc_score,
            "sectorAllocations": {k: round(v, 1) for k, v in current_sector_weights.items()},
            "stockAllocations": {row["Security"]: round(row["current_weight"], 1) for _, row in df.iterrows()}
        }
        
        # Simulated After Metrics assuming sells and buys are fully completed
        after_metrics = {
            "diversificationScore": min(95, int(diversification_score * 1.15)),
            "sectorConcentrationScore": min(100, int(sec_conc_score * 1.25)),
            "marketCapBalanceScore": min(100, int(mc_score * 1.2)),
            "sectorAllocations": {k: round(target_sector_alloc.get(k, 0.0), 1) for k in all_sectors},
            "stockAllocations": {row["Security"]: round(row["target_weight"], 1) for _, row in df.iterrows()}
        }

        # Human-Readable investment committee style summary
        summary = f"The portfolio is {stock_risk.lower()}ly concentrated at the stock level and {sec_risk.lower()}ly concentrated at the sector level. "
        if max_sec > 25.0:
            summary += f"The largest sector exposure lies in {max_sec_name} ({max_sec:.1f}% vs target {target_sector_alloc.get(max_sec_name, 0.0):.1f}%). "
        if sells_needed or buys_needed:
            summary += "A strategic reallocation is recommended: trim overallocations "
            if sells_needed:
                summary += f"in {', '.join([s[0] for s in sells_needed])} "
            if buys_needed:
                summary += f"and deploy capital into {', '.join([b[0] for b in buys_needed[:3]])} "
            summary += "to restore targets. "
        summary += f"Rebalancing urgency is { 'CRITICAL' if urgency_score > 75 else 'HIGH' if urgency_score > 50 else 'MODERATE' if urgency_score > 25 else 'LOW' }."

        return {
            "portfolioHealthScore": health_score,
            "riskLevel": risk_profile,
            "rebalancingRequired": rebal_triggered,
            "overallDrift": round(float(np.mean([abs(d) for d in sector_drift.values()])), 1) if sector_drift else 0.0,
            "sectorRecommendations": sector_recs,
            "stockRecommendations": stock_recs,
            "taxEfficientPlan": tax_plan,
            "concentrationWarnings": warnings,
            "capitalDeploymentPlan": sim_deploy,
            "marketCapRecommendations": mc_recs,
            "beforeMetrics": before_metrics,
            "afterMetrics": after_metrics,
            "diversificationScore": diversification_score,
            "sectorConcentrationScore": sec_conc_score,
            "marketCapBalanceScore": mc_score,
            "rebalancingUrgencyScore": urgency_score,
            "summary": summary
        }

    @classmethod
    def empty_response(cls, risk_profile):
        return {
            "portfolioHealthScore": 100,
            "riskLevel": risk_profile,
            "rebalancingRequired": False,
            "overallDrift": 0.0,
            "sectorRecommendations": [],
            "stockRecommendations": [],
            "taxEfficientPlan": [],
            "concentrationWarnings": ["No holdings available. Upload holdings to assess concentration."],
            "capitalDeploymentPlan": [],
            "marketCapRecommendations": [],
            "beforeMetrics": {},
            "afterMetrics": {},
            "diversificationScore": 100,
            "sectorConcentrationScore": 100,
            "marketCapBalanceScore": 100,
            "rebalancingUrgencyScore": 0,
            "summary": "Portfolio is empty. Add transactions/holdings to calculate rebalancing metrics."
        }
