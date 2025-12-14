import os

# List of files that might have the wrong port
files_to_check = [
    os.path.join('web_app', 'app.py'),
    os.path.join('client', 'enroll_client.py')
]

print("--- SCANNING FOR PORT 5001 ---")

for file_path in files_to_check:
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # If we find the old port 5001, replace it with 50051
            if '5001' in content:
                print(f"Found old port 5001 in: {file_path}")
                new_content = content.replace('5001', '50051')
                
                with open(file_path, 'w') as f:
                    f.write(new_content)
                print(f"✅ Fixed {file_path} -> Updated to 50051")
            else:
                print(f"👍 {file_path} is already correct (no 5001 found).")
                
        except Exception as e:
            print(f"❌ Could not read {file_path}: {e}")
    else:
        print(f"⚠️  Skipped {file_path} (File not found)")