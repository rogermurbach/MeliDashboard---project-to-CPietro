import pandas as pd
import json
from pyscript import window
from pyodide.ffi import to_js


def normalize_column(c):
    """Normalize column names: strip, lower, remove newlines and accents"""
    import unicodedata
    if c is None:
        return ''
    s = str(c).strip().lower().replace('\n', ' ').replace('\r', ' ')
    s = ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')
    s = ''.join(ch for ch in s if ch.isalnum() or ch in [' ', '_', '-'])
    s = ' '.join(s.split())
    return s


def find_column(df, names):
    """Find a dataframe column from candidate list"""
    for n in names:
        if n in df.columns:
            return n
    return None


def to_numeric_column(df, col):
    """Parse numeric columns safely, handling currency symbols"""
    if col and col in df.columns:
        # Check if values use comma or period as decimal separator
        sample = df[col].dropna().astype(str).iloc[0] if len(df[col].dropna()) > 0 else ""
        
        # If comma is decimal separator (Brazilian format: 1.234,56)
        if ',' in sample and '.' in sample:
            # Brazilian format: remove thousand separator (.) and replace decimal (,) with (.)
            return pd.to_numeric(
                df[col].astype(str)
                .str.replace(r'[^0-9,.-]', '', regex=True)
                .str.replace('.', '', regex=False)
                .str.replace(',', '.', regex=False),
                errors='coerce'
            )
        elif ',' in sample:
            # Only comma present, assume it's decimal separator
            return pd.to_numeric(
                df[col].astype(str)
                .str.replace(r'[^0-9,.-]', '', regex=True)
                .str.replace(',', '.', regex=False),
                errors='coerce'
            )
        else:
            # Period is decimal separator (US/International format: 1,234.56) or no formatting
            # Remove only currency symbols and thousand separators (commas)
            return pd.to_numeric(
                df[col].astype(str)
                .str.replace(r'[^0-9.-]', '', regex=True),
                errors='coerce'
            )
    else:
        return pd.Series([float('nan')] * len(df))


def process_data(input_json):
    """
    Main processing function: receives JSON data, returns processed metrics
    """
    # Convert JavaScript proxy object to Python
    # Use .to_py() method available on JsProxy objects
    data_list = input_json.to_py()
    
    # Create DataFrame
    df = pd.DataFrame(data_list)
    
    # Normalize column names
    orig_cols = list(df.columns)
    col_map = {orig: normalize_column(orig) for orig in orig_cols}
    df = df.rename(columns=col_map)
    
    # Known column name candidates (normalized)
    candidates = {
        'date_from': ['desde', 'from', 'data inicio', 'data', 'date from', 'start date', 'data de inicio'],
        'date_to': ['ate', 'até', 'to', 'data fim', 'data final', 'end date', 'data de fim'],
        'campaign': ['campanha', 'campaign', 'campaign name', 'campaign_name', 'titulo do anuncio patrocinado', 'titulo do anuncio'],
        'title': ['titulo do anuncio patrocinado', 'titulo', 'title'],
        'code': ['codigo do anuncio', 'codigo', 'code', 'id anuncio'],
        'status': ['status', 'estado'],
        'impressions': ['impressões', 'impressao', 'impressions', 'impr'],
        'clicks': ['cliques', 'clicks', 'click'],
        'cpc': ['cpc (custo por clique)', 'cpc', 'cpc ( custo por clique )'],
        'ctr': ['ctr (click through rate)', 'ctr', 'ctr (click through rate)'],
        'cvr': ['cvr (conversion rate)', 'cvr', 'conversion rate'],
        'revenue': ['receita (moeda local)', 'receita', 'revenue', 'receita'],
        'investment': ['investimento (moeda local)', 'investimento', 'spend', 'investment', 'gasto'],
        'acos': ['acos (investimento / receitas)', 'acos', 'acos ( investimento / receitas)'],
        'roas': ['roas (receitas / investimento)', 'roas', 'roas ( receitas / investimento)'],
        'sales_direct': ['vendas diretas', 'vendas diretas'],
        'sales_indirect': ['vendas indiretas', 'vendas indiretas'],
        'sales_total': ['vendas por publicidade (diretas + indiretas)', 'vendas por publicidade', 'vendas por publicidade (diretas + indiretas)'],
        'rev_direct': ['receita por vendas diretas (moeda local)', 'receita por vendas diretas', 'receita por vendas diretas (moeda local)'],
        'rev_indirect': ['receita por vendas indiretas', 'receita por vendas indiretas']
    }
    
    # Map columns
    mapped = {}
    for key, names in candidates.items():
        mapped[key] = find_column(df, names)
    
    # Parse numeric columns
    impr = to_numeric_column(df, mapped['impressions'])
    clicks = to_numeric_column(df, mapped['clicks'])
    spend = to_numeric_column(df, mapped['investment'])
    revenue = to_numeric_column(df, mapped['revenue'])
    sales_total = to_numeric_column(df, mapped['sales_total'])
    
    # Helper function to try parsing dates with multiple formats
    def try_parse_dates(col_data):
        if len(col_data.dropna()) == 0:
            return None
        
        # First, check if the data is already datetime (from Excel)
        if pd.api.types.is_datetime64_any_dtype(col_data):
            return col_data
        
        # Handle Excel serial date numbers (e.g., 45123 -> 2023-08-01)
        try:
            nums = pd.to_numeric(col_data, errors='coerce')
            valid_num = nums.dropna()
            if len(valid_num) > 0:
                median_val = float(valid_num.median())
                # Typical Excel serial day numbers fall roughly in this range for modern dates
                if 20000 <= median_val <= 90000:
                    dt = pd.to_datetime(valid_num, unit='D', origin='1899-12-30')
                    # Reconstruct full series aligning index
                    result = pd.Series(index=col_data.index, dtype='datetime64[ns]')
                    result.loc[valid_num.index] = dt
                    if result.notna().sum() > 0:
                        return result
        except Exception:
            pass
        
        sample_value = str(col_data.dropna().iloc[0]).strip()
        
        # List of formats to try - prioritize Portuguese and English formats
        formats_to_try = [
            "%d-%b-%Y",      # 01-Jan-2025, 01-Oct-2024 (English)
            "%d-%b-%Y",      # 01-set-2025, 01-out-2024 (Portuguese) - same format, different locale
            "%d-%B-%Y",      # 01-January-2025 (English)
            "%d-%B-%Y",      # 01-setembro-2025 (Portuguese)
            "%d/%m/%Y",      # 01/10/2024
            "%m/%d/%Y",      # 10/01/2024
            "%Y-%m-%d",      # 2024-10-01
            "%d-%m-%Y",      # 01-10-2024
            "%Y/%m/%d",      # 2024/10/01
            "%d-%b-%y",      # 01-Jan-25
        ]
        
        # Try Portuguese month mapping manually first
        portuguese_months = {
            'jan': 'Jan', 'fev': 'Feb', 'mar': 'Mar', 'abr': 'Apr', 'mai': 'May', 'jun': 'Jun',
            'jul': 'Jul', 'ago': 'Aug', 'set': 'Sep', 'out': 'Oct', 'nov': 'Nov', 'dez': 'Dec'
        }
        
        # Try Portuguese format by replacing month abbreviations
        try:
            port_series = col_data.astype(str).str.strip()
            for pt_abbr, en_abbr in portuguese_months.items():
                port_series = port_series.str.replace(f'-{pt_abbr}-', f'-{en_abbr}-', case=False, regex=False)
            result = pd.to_datetime(port_series, format="%d-%b-%Y", errors='coerce')
            if result.notna().sum() > 0:
                return result
        except:
            pass
        
        # Try each format
        for fmt in formats_to_try:
            try:
                result = pd.to_datetime(col_data.astype(str).str.strip(), format=fmt, errors='coerce')
                # If we got ANY valid dates, return them
                if result.notna().sum() > 0:
                    return result
            except:
                continue
        
        # Try without format specification (let pandas infer)
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = pd.to_datetime(col_data, errors='coerce')
                if result.notna().sum() > 0:
                    return result
        except:
            pass
        
        return None
    
    # Dates: Get both start and end dates from first two columns (A and B)
    date_start = None
    date_end = None
    
    # Try first column (A) as start date (explicit format from requirement)
    if len(df.columns) > 0:
        first_col = df.columns[0]
        try:
            ds = pd.to_datetime(df[first_col].astype(str).str.strip(), format="%d-%b-%Y", errors='coerce')
        except Exception:
            ds = None
        if ds is None or ds.notna().sum() == 0:
            ds = try_parse_dates(df[first_col])
        date_start = ds
    
    # Try second column (B) as end date (explicit format from requirement)
    if len(df.columns) > 1:
        second_col = df.columns[1]
        try:
            de = pd.to_datetime(df[second_col].astype(str).str.strip(), format="%d-%b-%Y", errors='coerce')
        except Exception:
            de = None
        if de is None or de.notna().sum() == 0:
            de = try_parse_dates(df[second_col])
        date_end = de
    
    # If first two columns didn't work, try mapped columns
    if date_start is None or (date_start is not None and date_start.isna().all()):
        if mapped['date_from'] and mapped['date_from'] in df.columns:
            date_start = try_parse_dates(df[mapped['date_from']])
    
    if date_end is None or (date_end is not None and date_end.isna().all()):
        if mapped['date_to'] and mapped['date_to'] in df.columns:
            date_end = try_parse_dates(df[mapped['date_to']])
    
    # Build processed dataframe
    proc = pd.DataFrame()
    # Avoid converting NaN/None to string literals like 'nan' or 'None'
    if mapped['campaign'] in df.columns:
        _src_campaign = df[mapped['campaign']]
    else:
        _src_campaign = df.get(mapped['title'], pd.Series([''] * len(df)))
    proc['campaign'] = _src_campaign.fillna('').astype(str)
    
    # Use title column for charts if available
    if mapped['title'] in df.columns:
        _src_title = df[mapped['title']]
    else:
        _src_title = _src_campaign
    proc['title'] = _src_title.fillna('').astype(str)
    
    proc['date_start'] = date_start
    proc['date_end'] = date_end
    proc['impressions'] = impr
    proc['clicks'] = clicks
    proc['spend'] = spend
    proc['revenue'] = revenue
    proc['sales_total'] = sales_total
    
    # Derived metrics - handle division by zero
    proc['ctr'] = proc['clicks'] / proc['impressions'].replace(0, float('nan'))
    proc['cpc'] = proc['spend'] / proc['clicks'].replace(0, float('nan'))
    proc['roas'] = proc['revenue'] / proc['spend'].replace(0, float('nan'))
    proc['acos'] = proc['spend'] / proc['revenue'].replace(0, float('nan'))
    
    # KPIs overall
    total_invest = float(proc['spend'].sum(skipna=True) or 0.0)
    total_revenue = float(proc['revenue'].sum(skipna=True) or 0.0)
    roas_mean = float(proc['roas'].mean(skipna=True) or 0.0)
    acos_mean = float(proc['acos'].mean(skipna=True) or 0.0)
    cpc_mean = float(proc['cpc'].mean(skipna=True) or 0.0)
    total_impr = int(proc['impressions'].sum(skipna=True) or 0)
    total_clicks = int(proc['clicks'].sum(skipna=True) or 0)
    
    # Daily aggregation (by date_start)
    daily = None
    if 'date_start' in proc.columns and proc['date_start'].notna().any():
        # Ensure we have a string date column to group by and to expose as 'date'
        proc['_date_start_str'] = pd.to_datetime(proc['date_start'], errors='coerce').dt.strftime('%Y-%m-%d')
        daily = proc.groupby('_date_start_str').agg({
            'impressions': 'sum',
            'clicks': 'sum',
            'spend': 'sum',
            'revenue': 'sum'
        }).reset_index().rename(columns={'_date_start_str': 'date'})
        daily['ctr'] = daily['clicks'] / daily['impressions'].replace(0, float('nan'))
        daily['cpc'] = daily['spend'] / daily['clicks'].replace(0, float('nan'))
        daily['roas'] = daily['revenue'] / daily['spend'].replace(0, float('nan'))
        # Sort chronologically and format display as dd/mm/YYYY
        daily['_dt'] = pd.to_datetime(daily['date'], format='%Y-%m-%d', errors='coerce')
        daily = daily.sort_values('_dt').drop(columns=['_dt'])
        daily['date'] = pd.to_datetime(daily['date'], format='%Y-%m-%d', errors='coerce').dt.strftime('%d/%m/%Y')
    
    # Convert date columns to strings for table display
    def _fmt_date_series(s):
        try:
            s_dt = pd.to_datetime(s, errors='coerce')
            out = s_dt.dt.strftime('%d/%m/%Y')
            return out.fillna('')
        except Exception:
            return pd.Series([''] * len(s))
    if 'date_start' in proc.columns:
        proc['date_start'] = _fmt_date_series(proc['date_start'])
    if 'date_end' in proc.columns:
        proc['date_end'] = _fmt_date_series(proc['date_end'])
    
    # Top campaigns by spend and ROAS
    top_spend = proc.groupby('campaign').agg({'spend': 'sum'}).reset_index().sort_values('spend', ascending=False).head(10)
    top_roas = proc.groupby('campaign').agg({'revenue': 'sum', 'spend': 'sum'}).reset_index()
    top_roas['roas'] = top_roas['revenue'] / top_roas['spend'].replace(0, float('nan'))
    top_roas = top_roas.sort_values('roas', ascending=False).head(10)
    
    # Top campaigns by Sales per Investment (Vendas por Investimento) - use title
    top_sales_investment = proc.groupby('title').agg({'sales_total': 'sum', 'spend': 'sum'}).reset_index()
    top_sales_investment['sales_per_investment'] = top_sales_investment['sales_total'] / top_sales_investment['spend'].replace(0, float('nan'))
    top_sales_investment = top_sales_investment.sort_values('sales_per_investment', ascending=False).head(10)
    
    # Prepare outputs as pure python structures (serializable)
    result = {
        'kpis': {
            'total_invest': total_invest,
            'total_revenue': total_revenue,
            'roas_mean': roas_mean,
            'acos_mean': acos_mean,
            'cpc_mean': cpc_mean,
            'total_impressions': int(total_impr),
            'total_clicks': int(total_clicks)
        },
        'daily': daily.to_dict(orient='records') if daily is not None else [],
        'top_spend': top_spend.to_dict(orient='records'),
        'top_roas': top_roas.to_dict(orient='records'),
        'top_sales_investment': top_sales_investment.to_dict(orient='records'),
        'processed_sample': proc.fillna('').to_dict(orient='records'),
    }
    
    return result


# Expose function to JavaScript
window.processDataPython = process_data
