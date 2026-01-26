import streamlit as st
import json
from pathlib import Path
import tempfile
from main import create_boxes

st.set_page_config(page_title="PDF Boxes", page_icon="📦", layout="wide")

# Session state
if 'expanded' not in st.session_state:
    st.session_state.expanded = set()
if 'viewing' not in st.session_state:
    st.session_state.viewing = None

st.title("PDF Box Creator")
st.caption("Extract hierarchical structure from PDFs")

uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])

if uploaded_file:
    if st.button("Process PDF", type="primary"):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        with st.spinner("Processing..."):
            try:
                full_path, index_path = create_boxes(tmp_path)
                
                with open(index_path) as f:
                    index = json.load(f)
                with open(full_path) as f:
                    full = json.load(f)
                
                st.session_state.index = index
                st.session_state.full = full
                st.session_state.expanded = set()
                st.session_state.viewing = None
                st.success("Processing complete")
                
            except Exception as e:
                st.error(f"Error: {e}")
                st.exception(e)
        
        Path(tmp_path).unlink(missing_ok=True)

# Display results
if 'index' in st.session_state:
    index = st.session_state.index
    full = st.session_state.full
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Pages", index['total_pages'])
    with col2:
        st.metric("Boxes", index['total_boxes'])
    with col3:
        st.metric("Levels", index['hierarchy_levels'])
    with col4:
        top = sum(1 for b in index['box_index'] if b['level'] == 1)
        st.metric("Chapters", top)
    
    st.divider()
    
    # Build tree
    def build_tree(boxes):
        tree = {}
        for box in boxes:
            tree[box['box_id']] = {**box, 'children': []}
        
        roots = []
        for box in boxes:
            if box['parent_id'] is None:
                roots.append(tree[box['box_id']])
            else:
                if box['parent_id'] in tree:
                    tree[box['parent_id']]['children'].append(tree[box['box_id']])
        
        return roots
    
    # Render tree item
    def render_item(node, level=0):
        box_id = node['box_id']
        has_children = len(node['children']) > 0
        is_expanded = box_id in st.session_state.expanded
        is_viewing = st.session_state.viewing == box_id
        
        # Indent
        indent = "│   " * level
        
        # Build display line
        if has_children:
            icon = "▾ " if is_expanded else "▸ "
        else:
            icon = "  "
        
        display = f"{indent}{icon}{node['title']}"
        page_info = f"p.{node['page_start']}-{node['page_end']}"
        
        # Create button for the item
        col1, col2 = st.columns([0.85, 0.15])
        
        with col1:
            if st.button(
                display,
                key=f"btn_{box_id}",
                use_container_width=True,
                type="secondary" if is_viewing else "secondary"
            ):
                if has_children:
                    # Toggle expand
                    if is_expanded:
                        st.session_state.expanded.discard(box_id)
                    else:
                        st.session_state.expanded.add(box_id)
                else:
                    # Show content
                    st.session_state.viewing = box_id
                st.rerun()
        
        with col2:
            st.caption(page_info)
        
        # Show content if viewing
        if is_viewing and not has_children:
            full_box = next(b for b in full['boxes'] if b['box_id'] == box_id)
            
            with st.container():
                st.markdown("---")
                st.subheader(full_box['title'])
                st.caption(f"Pages {full_box['page_start']}-{full_box['page_end']} • {full_box['char_count']:,} characters")
                
                st.text_area(
                    "Content",
                    full_box['text'],
                    height=500,
                    key=f"content_{box_id}",
                    label_visibility="collapsed"
                )
                
                if st.button("Close", key=f"close_{box_id}"):
                    st.session_state.viewing = None
                    st.rerun()
                
                st.markdown("---")
        
        # Show children if expanded
        if is_expanded and has_children:
            for child in sorted(node['children'], key=lambda x: x['page_start']):
                render_item(child, level + 1)
    
    # Render tree
    st.subheader("Structure")
    
    roots = build_tree(index['box_index'])
    for root in sorted(roots, key=lambda x: x['page_start']):
        render_item(root, 0)
    
    # Downloads
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            "Download Index",
            data=json.dumps(index, indent=2, ensure_ascii=False),
            file_name=f"{uploaded_file.name}_index.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        st.download_button(
            "Download Full Boxes",
            data=json.dumps(full, indent=2, ensure_ascii=False),
            file_name=f"{uploaded_file.name}_boxes.json",
            mime="application/json",
            use_container_width=True
        )

else:
    st.info("Upload a PDF to begin")
