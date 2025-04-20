"""Utilities for asset management in Starblitz Assault."""

import os
from pathlib import Path
from typing import Optional

def get_asset_path(asset_type: str, filename: str) -> str:
    """Get the correct path to an asset file that works in both development and installed modes.
    
    Args:
        asset_type: Type of asset ('images', 'music', 'sounds', etc.)
        filename: Name of the asset file
        
    Returns:
        Path to the asset as a string
    """
    # First, try to find the asset relative to the module's location
    try:
        # This will work when running as an installed package
        # Go up to the package root from utilities/asset_helper.py
        package_path = Path(__file__).parent.parent
        asset_path = package_path / "assets" / asset_type / filename
        if asset_path.exists():
            return str(asset_path)
    except (TypeError, ValueError):
        pass
    
    # Next, try the standard path relative to current working directory
    standard_path = os.path.join("assets", asset_type, filename)
    if os.path.exists(standard_path):
        return standard_path
    
    # Check if we're running from the project root
    project_path = os.path.join(os.getcwd(), "assets", asset_type, filename)
    if os.path.exists(project_path):
        return project_path
    
    # If all else fails, return the standard path and let the caller handle the error
    return standard_path 
