from pathlib import Path

env_file = Path(__file__).parent / ".env"

print(f"Looking for .env at: {env_file}")
print(f"File exists: {env_file.exists()}")

if env_file.exists():
    print(f"File size: {env_file.stat().st_size} bytes")

    # Read raw bytes
    raw_content = env_file.read_bytes()
    print(f"Raw bytes (first 100): {raw_content[:100]}")

    # Read as text
    text_content = env_file.read_text(encoding='utf-8')
    print(f"\nText content:\n{repr(text_content)}")

    # Parse line by line
    print("\nParsing lines:")
    for i, line in enumerate(text_content.splitlines(), 1):
        print(f"Line {i}: {repr(line)}")
        if '=' in line:
            key, value = line.split('=', 1)
            print(f"  Key: {repr(key)}, Value: {repr(value[:10])}...")