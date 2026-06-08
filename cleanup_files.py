"""
Utility to clean up all data files (CSVs, Excel files with holdings/stocks).
"""
import os
from pathlib import Path


def find_data_files():
    """Find all potential holdings/stock data files in the project."""
    project_root = Path(__file__).parent
    data_extensions = ['.csv', '.xlsx', '.xls']
    data_keywords = ['holding', 'stock', 'portfolio', 'price', 'shares', 'position']
    
    found_files = []
    
    # Search in common directories
    search_dirs = [
        project_root,
        project_root / 'data',
        project_root / 'uploads',
        project_root / 'files',
    ]
    
    for search_dir in search_dirs:
        if search_dir.exists():
            for file_path in search_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix in data_extensions:
                    # Check if filename contains data keywords
                    filename_lower = file_path.name.lower()
                    if any(keyword in filename_lower for keyword in data_keywords):
                        found_files.append(file_path)
    
    return found_files


def show_data_summary():
    """Show all data sources in the system."""
    print("\n" + "="*60)
    print("  InvestIQ Data Cleanup Utility")
    print("="*60 + "\n")
    
    print("📁 Data Files Found:\n")
    
    data_files = find_data_files()
    
    if data_files:
        for i, file_path in enumerate(data_files, 1):
            size_kb = file_path.stat().st_size / 1024
            print(f"   {i}. {file_path.name}")
            print(f"      Location: {file_path}")
            print(f"      Size: {size_kb:.2f} KB\n")
    else:
        print("   ✅ No data files found in project\n")
    
    # Database files
    print("💾 Database Files:\n")
    db_root = Path(__file__).parent / 'data'
    if db_root.exists():
        for db_file in db_root.glob('*.db'):
            size_kb = db_file.stat().st_size / 1024
            print(f"   • {db_file.name}")
            print(f"      Size: {size_kb:.2f} KB\n")
    else:
        print("   ✅ No database files found\n")
    
    return data_files


def delete_data_files(file_list):
    """Delete specified data files."""
    if not file_list:
        print("✅ No files to delete\n")
        return
    
    print(f"\n🗑️  Deleting {len(file_list)} file(s)...\n")
    
    for file_path in file_list:
        try:
            file_path.unlink()
            print(f"   ✓ Deleted: {file_path.name}")
        except Exception as e:
            print(f"   ✗ Failed to delete {file_path.name}: {e}")
    
    print("\n✅ Cleanup complete!\n")


if __name__ == "__main__":
    data_files = show_data_summary()
    
    if data_files:
        response = input("⚠️  Delete all data files above? (type 'yes' to confirm): ").strip().lower()
        if response == 'yes':
            delete_data_files(data_files)
        else:
            print("❌ Cancelled. No files were deleted.\n")
    
    print("="*60 + "\n")
