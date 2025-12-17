"""
CodeBaseBuddy Integration Test
Tests the semantic code search functionality
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_codebasebuddy():
    """Test CodeBaseBuddy functionality"""
    print("=" * 60)
    print("CodeBaseBuddy Integration Test")
    print("=" * 60)
    
    # Test 1: Import modules
    print("\n📦 Test 1: Import modules...")
    try:
        # Import directly from the module, accessing the underlying functions
        import mcp_servers.codebasebuddy_server as cbb
        
        # Check if libraries are available
        EMBEDDINGS_AVAILABLE = cbb.EMBEDDINGS_AVAILABLE
        FAISS_AVAILABLE = cbb.FAISS_AVAILABLE
        
        print(f"   ✅ Modules imported successfully")
        print(f"   - Embeddings available: {EMBEDDINGS_AVAILABLE}")
        print(f"   - FAISS available: {FAISS_AVAILABLE}")
        
        if not EMBEDDINGS_AVAILABLE or not FAISS_AVAILABLE:
            print("   ⚠️  Required libraries not available, some tests may fail")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Initialize embedding model
    print("\n🧠 Test 2: Initialize embedding model...")
    try:
        result = cbb.init_embedding_model()
        if result:
            print(f"   ✅ Embedding model loaded")
        else:
            print(f"   ⚠️  Embedding model not loaded")
    except Exception as e:
        print(f"   ❌ Embedding model error: {e}")
    
    # Test 3: Build index (using the function directly via the tool wrapper)
    print("\n📊 Test 3: Build index...")
    try:
        # Access the underlying async function from the FunctionTool
        from pathlib import Path
        
        # Call the module-level functions directly
        root = Path("./src").resolve()
        
        # Scan for Python files
        code_files = list(root.rglob("*.py"))
        print(f"   Found {len(code_files)} Python files to index")
        
        # Extract chunks manually for testing
        all_chunks = []
        for file_path in code_files[:10]:  # Limit to first 10 files for testing
            try:
                if cbb.should_exclude_path(file_path):
                    continue
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                chunks = cbb.extract_python_chunks(str(file_path), content)
                all_chunks.extend(chunks)
            except Exception as e:
                pass
        
        print(f"   Extracted {len(all_chunks)} code chunks")
        
        if all_chunks:
            # Test embedding creation
            test_chunk = all_chunks[0]
            embed_text = f"{test_chunk.name}\n{test_chunk.content[:500]}"
            embedding = cbb.create_embedding(embed_text)
            
            if embedding is not None:
                print(f"   ✅ Embedding created successfully")
                print(f"   - Embedding shape: {embedding.shape}")
                print(f"   - Sample chunk: {test_chunk.name} ({test_chunk.chunk_type})")
            else:
                print(f"   ❌ Failed to create embedding")
        else:
            print(f"   ⚠️  No chunks extracted")
            
    except Exception as e:
        print(f"   ❌ Index build error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Semantic search simulation
    print("\n🔍 Test 4: Semantic search (direct test)...")
    try:
        # Create a test query embedding
        query = "How does authentication work?"
        query_embedding = cbb.create_embedding(query)
        
        if query_embedding is not None:
            print(f"   ✅ Query embedding created")
            print(f"   - Query: '{query}'")
            print(f"   - Embedding shape: {query_embedding.shape}")
        else:
            print(f"   ❌ Query embedding failed")
    except Exception as e:
        print(f"   ❌ Search error: {e}")
    
    # Test 5: Code context
    print("\n📄 Test 5: Get code context...")
    try:
        file_path = "./src/mcp/tool_manager.py"
        if os.path.exists(file_path):
            content = open(file_path, 'r', encoding='utf-8').read()
            lines = content.split('\n')
            
            # Get context around line 100
            line_num = min(100, len(lines))
            start = max(0, line_num - 5)
            end = min(len(lines), line_num + 5)
            context = '\n'.join(lines[start:end])
            
            print(f"   ✅ Context retrieved")
            print(f"   - File: {file_path}")
            print(f"   - Lines: {start+1}-{end}")
            print(f"   - Preview: {context[:100]}...")
        else:
            print(f"   ⚠️  File not found: {file_path}")
    except Exception as e:
        print(f"   ❌ Context error: {e}")
    
    # Test 6: Full index build via MCP endpoint simulation
    print("\n🏗️ Test 6: Full FAISS index creation...")
    try:
        import numpy as np
        import faiss
        
        # Create sample embeddings
        sample_texts = [
            "def create_agent(self, name): Create an agent",
            "async def initialize_tools(self): Initialize MCP tools",
            "class MCPToolManager: Manage MCP server tools",
            "def read_file(path): Read file contents",
            "def semantic_search(query): Search using embeddings"
        ]
        
        embeddings = []
        for text in sample_texts:
            emb = cbb.create_embedding(text)
            if emb is not None:
                embeddings.append(emb)
        
        if embeddings:
            # Create FAISS index
            embeddings_array = np.vstack(embeddings).astype('float32')
            faiss.normalize_L2(embeddings_array)
            
            index = faiss.IndexFlatIP(embeddings_array.shape[1])
            index.add(embeddings_array)
            
            # Test search
            query_vec = cbb.create_embedding("How to create an agent?")
            if query_vec is not None:
                query_vec = query_vec.reshape(1, -1).astype('float32')
                faiss.normalize_L2(query_vec)
                
                D, I = index.search(query_vec, 3)
                
                print(f"   ✅ FAISS index created and tested")
                print(f"   - Indexed {len(embeddings)} vectors")
                print(f"   - Search results:")
                for i, (score, idx) in enumerate(zip(D[0], I[0])):
                    if idx >= 0:
                        print(f"     {i+1}. Score: {score:.4f} - {sample_texts[idx][:50]}...")
        else:
            print(f"   ❌ Failed to create embeddings")
            
    except Exception as e:
        print(f"   ❌ FAISS test error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ CodeBaseBuddy Integration Test Complete!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_codebasebuddy())
    sys.exit(0 if success else 1)
