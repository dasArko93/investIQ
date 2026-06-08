class SectorEngine:
    @staticmethod
    def sector_allocation(df):
        if df.empty or "Sub-Sector" not in df:
            return df
        return df.groupby("Sub-Sector")["Current Value Rs"].sum().sort_values(ascending=False)
