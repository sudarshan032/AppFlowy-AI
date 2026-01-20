import pydantic
print(f"Pydantic version: {pydantic.VERSION}")
try:
    import chromadb
    print("Chromadb imported successfully")
except Exception as e:
    import traceback
    traceback.print_exc()
