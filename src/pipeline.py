"""
Data processing pipeline for Nassau Candy order data.
Handles data cleaning, transformation, and enrichment.
"""

import pandas as pd
import numpy as np
from datetime import datetime


def process_dataset(df, is_nassau=False):
    """
    Process and enrich the Nassau Candy dataset.
    
    Args:
        df (pd.DataFrame): Raw dataset with order data
        is_nassau (bool): Whether this is Nassau Candy data
        
    Returns:
        pd.DataFrame: Processed dataset with computed fields
    """
    
    df_processed = df.copy()
    
    # Convert date columns
    if 'Order Date' in df_processed.columns:
        df_processed['Order Date'] = pd.to_datetime(df_processed['Order Date'], format='%d-%m-%Y', errors='coerce')
    
    if 'Ship Date' in df_processed.columns:
        df_processed['Ship Date'] = pd.to_datetime(df_processed['Ship Date'], format='%d-%m-%Y', errors='coerce')
    
    # Ensure numeric columns
    numeric_columns = ['Sales', 'Units', 'Cost', 'Gross Profit']
    for col in numeric_columns:
        if col in df_processed.columns:
            df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce')
    
    # Calculate derived metrics
    if 'Sales' in df_processed.columns and 'Gross Profit' in df_processed.columns:
        df_processed['Gross Margin %'] = (
            (df_processed['Gross Profit'] / df_processed['Sales'] * 100)
            .round(2)
        )
    
    if 'Gross Profit' in df_processed.columns and 'Units' in df_processed.columns:
        df_processed['Profit per Unit'] = (
            (df_processed['Gross Profit'] / df_processed['Units'])
            .round(2)
        )
    
    if 'Sales' in df_processed.columns and 'Units' in df_processed.columns:
        df_processed['Price per Unit'] = (
            (df_processed['Sales'] / df_processed['Units'])
            .round(2)
        )
    
    # Calculate shipping time
    if 'Order Date' in df_processed.columns and 'Ship Date' in df_processed.columns:
        df_processed['Shipping Days'] = (
            (df_processed['Ship Date'] - df_processed['Order Date']).dt.days
        )
    
    # Categorize margin tier
    if 'Gross Margin %' in df_processed.columns:
        df_processed['Margin Tier'] = df_processed['Gross Margin %'].apply(_categorize_margin)
    
    # Categorize sales volume
    if 'Sales' in df_processed.columns:
        df_processed['Sales Volume'] = pd.cut(
            df_processed['Sales'],
            bins=[0, 10, 50, 100, float('inf')],
            labels=['Low', 'Medium', 'High', 'Very High']
        )
    
    return df_processed


def _categorize_margin(margin):
    """
    Categorize gross margin percentage into tiers.
    
    Args:
        margin (float): Gross margin percentage
        
    Returns:
        str: Margin tier classification
    """
    if pd.isna(margin):
        return 'Unknown'
    elif margin >= 60:
        return 'Excellent (60%+)'
    elif margin >= 40:
        return 'Good (40-60%)'
    elif margin >= 20:
        return 'Fair (20-40%)'
    else:
        return 'Poor (<20%)'


def get_product_summary(df):
    """
    Generate product-level summary statistics.
    
    Args:
        df (pd.DataFrame): Processed dataset
        
    Returns:
        pd.DataFrame: Product performance summary
    """
    if 'Product Name' not in df.columns:
        return pd.DataFrame()
    
    summary = df.groupby('Product Name').agg({
        'Sales': ['sum', 'mean', 'count'],
        'Gross Profit': ['sum', 'mean'],
        'Gross Margin %': 'mean',
        'Units': 'sum'
    }).round(2)
    
    summary.columns = ['Total Sales', 'Avg Sales', 'Order Count', 'Total Profit', 
                       'Avg Profit', 'Avg Margin %', 'Total Units']
    
    return summary.sort_values('Total Sales', ascending=False)


def get_division_summary(df):
    """
    Generate division-level summary statistics.
    
    Args:
        df (pd.DataFrame): Processed dataset
        
    Returns:
        pd.DataFrame: Division performance summary
    """
    if 'Division' not in df.columns:
        return pd.DataFrame()
    
    summary = df.groupby('Division').agg({
        'Sales': 'sum',
        'Gross Profit': 'sum',
        'Gross Margin %': 'mean',
        'Units': 'sum',
        'Order ID': 'count'
    }).round(2)
    
    summary.columns = ['Total Sales', 'Total Profit', 'Avg Margin %', 'Total Units', 'Order Count']
    
    return summary.sort_values('Total Sales', ascending=False)


def get_regional_summary(df):
    """
    Generate region-level summary statistics.
    
    Args:
        df (pd.DataFrame): Processed dataset
        
    Returns:
        pd.DataFrame: Regional performance summary
    """
    if 'Region' not in df.columns:
        return pd.DataFrame()
    
    summary = df.groupby('Region').agg({
        'Sales': 'sum',
        'Gross Profit': 'sum',
        'Gross Margin %': 'mean',
        'Units': 'sum',
        'Order ID': 'count'
    }).round(2)
    
    summary.columns = ['Total Sales', 'Total Profit', 'Avg Margin %', 'Total Units', 'Order Count']
    
    return summary.sort_values('Total Sales', ascending=False)
