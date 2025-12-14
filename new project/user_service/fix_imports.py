import os

# Define the file path
file_path = os.path.join('user_service', 'user_pb2_grpc.py')

print(f"Checking {file_path}...")

try:
    with open(file_path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    fixed = False
    
    for line in lines:
        # Look for the specific problem line
        if 'import user_pb2 as user__pb2' in line and 'from .' not in line:
            print(f"Found broken line: {line.strip()}")
            # Replace it with the correct line
            new_lines.append('from . import user_pb2 as user__pb2\n')
            fixed = True
            print("--> Fixed it to: from . import user_pb2 as user__pb2")
        else:
            new_lines.append(line)

    if fixed:
        with open(file_path, 'w') as f:
            f.writelines(new_lines)
        print("✅ SUCCESS: File updated successfully.")
    else:
        print("ℹ️ INFO: File was already fixed or line not found.")

except FileNotFoundError:
    print("❌ ERROR: Could not find the file. Are you in 'D:\\new project'?")