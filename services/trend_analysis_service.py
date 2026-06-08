"""Analyze holdings trends and portfolio changes over time."""
import pandas as pd
from datetime import datetime
from database.db import SessionLocal
from database.models import Holding, TrendSnapshot
from sqlalchemy import func, distinct


class TrendAnalysisService:
    """Analyze portfolio composition changes and trends."""

    @staticmethod
    def compare_snapshots(snapshot_date_1, snapshot_date_2):
        """
        Compare two snapshots and identify differences (additions, removals, changes).
        
        Returns dict with:
        - added: new securities
        - removed: sold securities
        - increased: quantity/value increases
        - decreased: quantity/value decreases
        """
        db = SessionLocal()
        try:
            h1 = {h.security: h for h in db.query(Holding).filter(Holding.snapshot_date == snapshot_date_1).all()}
            h2 = {h.security: h for h in db.query(Holding).filter(Holding.snapshot_date == snapshot_date_2).all()}
            
            analysis = {
                'added': [],
                'removed': [],
                'increased': [],
                'decreased': []
            }
            
            # Find added and changed securities
            for sec, h2_record in h2.items():
                if sec not in h1:
                    analysis['added'].append({
                        'security': sec,
                        'quantity': h2_record.quantity,
                        'value': h2_record.current_value,
                        'pnl': h2_record.pnl
                    })
                else:
                    h1_record = h1[sec]
                    if h2_record.quantity > h1_record.quantity:
                        analysis['increased'].append({
                            'security': sec,
                            'quantity_change': h2_record.quantity - h1_record.quantity,
                            'value_before': h1_record.current_value,
                            'value_after': h2_record.current_value,
                            'pnl_change': h2_record.pnl - h1_record.pnl
                        })
                    elif h2_record.quantity < h1_record.quantity:
                        analysis['decreased'].append({
                            'security': sec,
                            'quantity_change': h1_record.quantity - h2_record.quantity,
                            'value_before': h1_record.current_value,
                            'value_after': h2_record.current_value,
                            'pnl_change': h2_record.pnl - h1_record.pnl
                        })
            
            # Find removed securities
            for sec in h1:
                if sec not in h2:
                    analysis['removed'].append({
                        'security': sec,
                        'quantity': h1[sec].quantity,
                        'value': h1[sec].current_value,
                        'pnl': h1[sec].pnl
                    })
            
            return analysis
        
        finally:
            db.close()

    @staticmethod
    def portfolio_trend_over_time():
        """Get portfolio value and composition trend over time."""
        db = SessionLocal()
        try:
            snapshots = db.query(
                Holding.snapshot_date,
                func.sum(Holding.current_value).label('total_value'),
                func.sum(Holding.pnl).label('total_pnl'),
                func.count(distinct(Holding.security)).label('holding_count')
            ).group_by(Holding.snapshot_date).order_by(Holding.snapshot_date).all()
            
            return [
                {
                    'snapshot_date': s[0],
                    'total_value': s[1],
                    'total_pnl': s[2],
                    'holding_count': s[3]
                }
                for s in snapshots
            ]
        
        finally:
            db.close()

    @staticmethod
    def sector_allocation_trend(snapshot_dates=None):
        """Track sector allocation changes across snapshots."""
        db = SessionLocal()
        try:
            if not snapshot_dates:
                snapshot_dates = db.query(func.distinct(Holding.snapshot_date)).all()
                snapshot_dates = [s[0] for s in snapshot_dates]
            
            trend = []
            for snap_date in sorted(snapshot_dates):
                holdings = db.query(Holding).filter(Holding.snapshot_date == snap_date).all()
                
                total_value = sum(h.current_value for h in holdings)
                sector_breakdown = {}
                
                # Group by sector (extract from security name or use sub_sector if available)
                for h in holdings:
                    sector = h.security.split()[0]  # Simplified: use first word
                    if sector not in sector_breakdown:
                        sector_breakdown[sector] = 0
                    sector_breakdown[sector] += h.current_value / total_value * 100 if total_value else 0
                
                trend.append({
                    'snapshot_date': snap_date,
                    'allocation': sector_breakdown
                })
            
            return trend
        
        finally:
            db.close()

    @staticmethod
    def get_holding_history(security):
        """Get complete history of a specific holding across all snapshots."""
        db = SessionLocal()
        try:
            history = db.query(Holding).filter(Holding.security == security).order_by(Holding.snapshot_date).all()
            
            return [
                {
                    'snapshot_date': h.snapshot_date,
                    'quantity': h.quantity,
                    'current_value': h.current_value,
                    'pnl': h.pnl,
                    'average_cost': h.average_cost
                }
                for h in history
            ]
        
        finally:
            db.close()
