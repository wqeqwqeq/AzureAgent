import asyncio
import re
import streamlit as st

async def az_login():
    # Create subprocess with asyncio
    proc = await asyncio.create_subprocess_exec(
        "az", "login", "--use-device-code", "--output", "none",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    
    # Check if stdout is available
    if proc.stdout is None:
        print("Error: Unable to read subprocess output")
        return
    
    # Read output line by line asynchronously
    async for line in proc.stdout:
        line = line.decode('utf-8').strip()
        if not line:
            continue
            
        if "https://" in line and "code" in line:
            url_match = re.search(r"https://\S+", line)
            code_match = re.search(r"code ([A-Z0-9-]{8,})", line)
            
            if url_match and code_match:
                url = url_match.group(0)
                code = code_match.group(1)
                print(url, code)
                break
    
    # Wait for the process to complete
    await proc.wait()

# Example usage
if __name__ == "__main__":
    asyncio.run(az_login()) 