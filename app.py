import streamlit as st
import os
import uuid
import datetime
from streamlit_agraph import agraph

# Local imports
from utils import data_manager
from utils import image_processor
from utils import graph_visualizer

# --- Configuration ---
st.set_page_config(
    page_title="DeepMemory",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
def local_css(file_name):
    with open(file_name, encoding='utf-8') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("assets/style.css")

# --- Session State Management ---
if 'step' not in st.session_state:
    st.session_state.step = 'input' # input, review
if 'detected_people' not in st.session_state:
    st.session_state.detected_people = [] 
if 'current_image_path' not in st.session_state:
    st.session_state.current_image_path = None
if 'graph_center' not in st.session_state:
    st.session_state.graph_center = None
if 'selected_node_id' not in st.session_state:
    st.session_state.selected_node_id = None

# --- Sidebar ---
st.sidebar.title("🌌 DeepMemory")
mode = st.sidebar.radio("Navigation", ["Relationship", "Time Capsule", "Memory Gallery"])

# --- View: Relationship ---
if mode == "Relationship":
    st.title("Relationship Graph")
    st.markdown("Explore the constellation of your memories.")
    
    nodes = data_manager.get_nodes()
    edges = data_manager.get_edges()
    
    # 1. Sidebar Controls
    view_depth = st.sidebar.slider("View Depth (k)", min_value=1, max_value=3, value=1)
    
    center = st.session_state.graph_center
    if st.sidebar.button("Reset View"):
        st.session_state.graph_center = None
        st.session_state.selected_node_id = None
        center = None
        st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.metric("Total Nodes", len(nodes))
    st.sidebar.metric("Connections", len(edges))
    
    with st.sidebar.expander("⚠️ Developer Options"):
        confirm_wipe = st.checkbox("⚠️ I confirm I want to wipe ALL data")
        if confirm_wipe:
            if st.button("🗑️ Reset All Memory", type="primary"):
                if data_manager.reset_database():
                    st.session_state.clear()
                    st.rerun()

    # 2. Layout Split
    col_main, col_info = st.columns([3, 1])
    
    with col_main:
        # Generate dynamic seed to force physics re-simulation on center change
        dynamic_seed = 42
        if center:
            # Use hash of center ID to ensure consistent but unique layout for each view
            dynamic_seed = abs(hash(center)) % 10000
            
        vis_nodes, vis_edges, config = graph_visualizer.get_graph_data(nodes, edges, center, k_hop=view_depth, seed=dynamic_seed)
        
        try:
            # Graph Component
            current_selection = agraph(nodes=vis_nodes, edges=vis_edges, config=config)
            
            # Update selection state only if changed
            if current_selection and current_selection != st.session_state.selected_node_id:
                st.session_state.selected_node_id = current_selection
                st.rerun()
                
        except Exception as e:
            st.warning(f"Graph visualizer refreshed. ({str(e)})")
            # Reset state on error to prevent loops
            st.session_state.graph_center = None
            st.rerun()

    # 3. Node Inspector Panel
    with col_info:
        st.subheader("Inspector")
        
        selected_id = st.session_state.selected_node_id
        if selected_id:
            # Find node data
            node_data = next((n for n in nodes if n['id'] == selected_id), None)
            
            if node_data:
                # Tabs for Profile and Timeline
                tab_profile, tab_timeline = st.tabs(["ℹ️ Profile", "📅 Timeline"])
                
                with tab_profile:
                    st.markdown(f"### {node_data.get('name', 'Unknown')}")
                    st.caption(f"ID: {node_data['id'][:8]}...")
                    
                    desc = node_data.get('description', 'No description available.')
                    st.info(desc)
                    
                    # Relation context
                    if center and center != selected_id:
                        # Find edge between center and selected
                        # Note: This checks direct connection only. For k-hop, logic might need bfs, 
                        # but for now let's show direct edge info if exists.
                        rel_text = "Indirect connection"
                        for e in edges:
                            if (e['source'] == center and e['target'] == selected_id) or \
                               (e['target'] == center and e['source'] == selected_id):
                                rel_text = e.get('relation_type', 'Connected')
                                break
                        st.markdown(f"**Relation to Center:** {rel_text}")
                    
                    st.markdown("---")
                    
                    # --- Avatar Settings ---
                    with st.expander("🎨 Avatar Settings"):
                        current_style = node_data.get('avatar_type', 'image')
                        style_choice = st.radio("Avatar Style", ["Image", "Solid Color"], 
                                                index=0 if current_style == 'image' else 1)
                        
                        if style_choice == "Image":
                            # Show current
                            avatar_path = os.path.join("assets", "avatars", f"{selected_id}.png")
                            if os.path.exists(avatar_path):
                                st.image(avatar_path, width=100, caption="Current Avatar")
                            else:
                                st.info("No custom avatar set.")
                                
                            new_avatar = st.file_uploader("Upload New Avatar", type=['png', 'jpg'])
                            if new_avatar:
                                if st.button("Save Avatar"):
                                    # Save file
                                    with open(avatar_path, "wb") as f:
                                        f.write(new_avatar.getbuffer())
                                    
                                    # Update Node
                                    node_data['avatar_type'] = 'image'
                                    data_manager.save_node(node_data)
                                    st.success("Avatar updated!")
                                    st.rerun()
                                    
                        elif style_choice == "Solid Color":
                            current_color = node_data.get('avatar_value', '#A8DADC')
                            new_color = st.color_picker("Choose Color", current_color)
                            
                            if st.button("Apply Color"):
                                node_data['avatar_type'] = 'color'
                                node_data['avatar_value'] = new_color
                                data_manager.save_node(node_data)
                                st.success("Color updated!")
                                st.rerun()

                    if st.button("📍 Set as New Center"):
                        st.session_state.graph_center = selected_id
                        st.session_state.selected_node_id = None # Clear selection or keep it? Let's clear to show focus.
                        st.rerun()

                    # --- Relationship Matrix Editor ---
                    st.markdown("---")
                    st.subheader("🔗 Edit Connections")
                    
                    # Prepare data for editor
                    other_nodes = [n for n in nodes if n['id'] != selected_id]
                    
                    # Helper to find existing relation
                    def get_relation(n_id):
                        key_sorted = tuple(sorted((selected_id, n_id)))
                        for e in edges:
                            if tuple(sorted((e['source'], e['target']))) == key_sorted:
                                return e.get('relation_type', 'Connected')
                        return "None"

                    import pandas as pd
                    
                    table_data = []
                    for n in other_nodes:
                        table_data.append({
                            "Target Node": n['name'],
                            "Relationship": get_relation(n['id']),
                            "Target ID": n['id'] # Hidden column for logic
                        })
                    
                    if table_data:
                        df = pd.DataFrame(table_data)
                        
                        edited_df = st.data_editor(
                            df,
                            column_config={
                                "Target Node": st.column_config.TextColumn(disabled=True),
                                "Relationship": st.column_config.TextColumn(required=True),
                                "Target ID": None # Hide ID
                            },
                            hide_index=True,
                            key=f"editor_{selected_id}"
                        )
                        
                        if st.button("Update Relationships"):
                            changes_made = False
                            for index, row in edited_df.iterrows():
                                target_id = row['Target ID']
                                new_label = row['Relationship'].strip()
                                old_label = get_relation(target_id)
                                
                                if new_label != old_label:
                                    if new_label.lower() in ["none", ""]:
                                        # Remove edge
                                        if old_label != "None":
                                            data_manager.remove_edge(selected_id, target_id)
                                            changes_made = True
                                    else:
                                        # Add/Update edge
                                        data_manager.add_edge(selected_id, target_id, new_label)
                                        changes_made = True
                            
                            if changes_made:
                                st.success("Graph updated!")
                                st.rerun()
                    else:
                        st.caption("No other nodes to connect to.")
                    
                    # --- Danger Zone ---
                    st.divider()
                    with st.expander("⚠️ Danger Zone"):
                        st.warning("Deleting this node is permanent. All connections will be removed.")
                        
                        confirm_del = st.checkbox(f"Confirm deletion of '{node_data.get('name')}'")
                        if st.button("🗑️ Delete Node", type="primary", disabled=not confirm_del):
                            data_manager.delete_node(selected_id)
                            st.success("Node deleted.")
                            st.session_state.selected_node_id = None
                            st.rerun()
                
                with tab_timeline:
                    st.subheader(f"History with {node_data.get('name', 'Unknown')}")
                    events = data_manager.get_events_for_node(selected_id)
                    
                    if not events:
                        st.caption("No shared memories recorded yet.")
                    
                    for evt in events:
                        with st.container(border=True):
                            col_date, col_badges = st.columns([1, 2])
                            with col_date:
                                st.caption(evt.get('date', 'Unknown Date'))
                            with col_badges:
                                # Check for Shared Memory (if current center is involved)
                                # Default center is 'root_me' if None? Or st.session_state.graph_center
                                current_viewer = center if center else 'root_me'
                                if current_viewer in evt.get('related_nodes', []):
                                    st.markdown("⭐ **Shared Memory**")
                            
                            st.markdown(f"**{evt.get('title', 'Memory')}**")
                            st.write(evt.get('content', ''))
                            
                            if evt.get('images'):
                                for img_path in evt['images']:
                                    if os.path.exists(img_path):
                                        st.image(img_path, use_container_width=True)
                
            else:
                st.write("Node not found in current data.")
        else:
            st.markdown("*Select a node to view details.*")
            if center:
                st.markdown(f"Current Center: **{next((n['name'] for n in nodes if n['id'] == center), center)}**")

# --- View: Time Capsule ---
elif mode == "Time Capsule":
    st.title("Time Capsule")
    
    if st.session_state.step == 'input':
        with st.form("memory_form"):
            date = st.date_input("Date", datetime.date.today())
            event_title = st.text_input("Event Title (Optional)", placeholder="e.g. Birthday Party")
            text = st.text_area("Journal Entry", height=150, placeholder="Tell me a story... (or upload a photo)")
            context_clues = st.text_area("📝 Scene Description & Clues (Optional)", placeholder="E.g. The man in blue is Bob...")
            uploaded_file = st.file_uploader("Upload Photo", type=['jpg', 'jpeg', 'png'])
            
            submitted = st.form_submit_button("Analyze Memory")
            
            if submitted:
                # Validation
                if not text and not uploaded_file:
                    st.error("Please provide either text or a photo.")
                    st.stop()
                
                # Store Form Data
                st.session_state.form_data = {
                    "date": str(date),
                    "title": event_title,
                    "content": text,
                    "context_clues": context_clues
                }
                
                results = []
                
                # A. Image Processing path
                if uploaded_file:
                    # Save file
                    assets_dir = os.path.join("assets")
                    if not os.path.exists(assets_dir): os.makedirs(assets_dir)
                    
                    file_ext = uploaded_file.name.split('.')[-1]
                    filename = f"{uuid.uuid4()}.{file_ext}"
                    filepath = os.path.join(assets_dir, filename)
                    
                    with open(filepath, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    st.session_state.current_image_path = filepath
                    
                    with st.spinner("AI is seeing..."):
                        results = image_processor.analyze_image_with_qwen(filepath, context_clues)
                
                # B. Text Processing path
                elif text and not uploaded_file:
                    with st.spinner("AI is reading..."):
                        results = image_processor.analyze_text_diary(text)
                        # Results structure: [{'name': 'Old Wang', 'relation': 'Neighbor', 'description': '...'}]
                        # Convert to common format for Review
                        normalized = []
                        for r in results:
                            normalized.append({
                                "description": r.get("description", "Mentioned in text"),
                                "suggested_name": r.get("name"),
                                "relation_type": r.get("relation")
                            })
                        results = normalized

                st.session_state.detected_people = results
                st.session_state.step = 'review'
                st.rerun()

    elif st.session_state.step == 'review':
        st.subheader("Memory Review & Tagging")
        
        # Display context
        if st.session_state.current_image_path:
            st.image(st.session_state.current_image_path, caption="Visual Memory", use_container_width=True)
        elif st.session_state.form_data.get("content"):
            st.info(f"**Text Memory**: \"{st.session_state.form_data['content']}\"")
            
        people_data = st.session_state.detected_people
        
        # Check for errors
        if people_data and isinstance(people_data[0], dict) and "error" in people_data[0]:
            st.error(people_data[0]["error"])
            if st.button("Back"):
                st.session_state.step = 'input'
                st.rerun()
        else:
            if not people_data:
                st.warning("No clear entities detected.")
            
            decisions = []
            known_nodes = data_manager.get_nodes()
            node_options = {n['name']: n['id'] for n in known_nodes}
            
            with st.form("review_form"):
                for i, person in enumerate(people_data):
                    desc = person.get("description", "Unknown")
                    suggested_name_from_text = person.get("suggested_name")
                    relation_from_text = person.get("relation_type")
                    
                    st.markdown(f"---")
                    st.markdown(f"### Entity #{i+1}")
                    st.caption(f"Trace: {desc}")
                    
                    # Smart Recall Logic
                    smart_suggestion = None
                    if not suggested_name_from_text: # If it's image based, try to match
                        match_result = image_processor.find_best_match(desc, known_nodes)
                        if match_result.get("match_found"):
                            smart_suggestion = match_result
                    
                    # Determine Default State
                    default_choice_idx = 0 # New Person
                    match_msg = ""
                    
                    if suggested_name_from_text:
                        # Text mode: Pre-fill name
                        match_msg = f"AI Identified: **{suggested_name_from_text}**"
                        # Check if this name already exists strictly?
                        if suggested_name_from_text in node_options:
                             default_choice_idx = 1 # Select Existing
                    
                    elif smart_suggestion:
                        match_msg = f"AI thinks this is: **{smart_suggestion['suggested_name']}**"
                        default_choice_idx = 1 # Select Existing
                        
                    if match_msg:
                        st.success(match_msg)
                    
                    # Controls
                    col1, col2 = st.columns(2)
                    
                    # Extra inputs container
                    manual_connections = []
                    connect_to_me = True
                    
                    with col1:
                        # Dynamic Options based on smart recall
                        options = ["New Person", "Select Existing", "Ignore"]
                        
                        choice = st.radio(
                            f"Identity Action", 
                            options,
                            index=default_choice_idx,
                            key=f"choice_{i}"
                        )
                        
                        # Relation Input (only relevant if connecting to Me or general label)
                        rel_val = relation_from_text if relation_from_text else ""
                        relation_input = st.text_input("Relationship to Me (e.g. friend)", value=rel_val, key=f"rel_{i}")

                    with col2:
                        # Name Inputs
                        prefill_new = suggested_name_from_text if suggested_name_from_text else ""
                        
                        # Logic Fix: If user explicitly switches to "New Person" from a potential match, 
                        # clear the name field so they can type the correct new name (avoiding "Bob" when it's "Alice")
                        if choice == "New Person" and suggested_name_from_text in node_options:
                             prefill_new = ""
                             
                        name_input = st.text_input(f"New Name", value=prefill_new, key=f"name_{i}")
                        
                        # Select Box
                        prefill_idx = 0
                        if smart_suggestion:
                             if smart_suggestion['suggested_name'] in node_options:
                                 # find index
                                 keys = [""] + list(node_options.keys())
                                 try:
                                     prefill_idx = keys.index(smart_suggestion['suggested_name'])
                                 except:
                                     pass
                        elif suggested_name_from_text and suggested_name_from_text in node_options:
                             keys = [""] + list(node_options.keys())
                             try:
                                 prefill_idx = keys.index(suggested_name_from_text)
                             except:
                                 pass

                        existing_select = st.selectbox(f"Select Existing", [""] + list(node_options.keys()), index=prefill_idx, key=f"sel_{i}")

                    # --- New Person: Advanced Edge Mapping ---
                    if choice == "New Person":
                        st.caption("Network Connections")
                        connect_to_me = st.checkbox("Connect to Me", value=True, key=f"conn_me_{i}")
                        
                        with st.expander("🔗 Define other connections (Optional)"):
                            # Filter out 'root_me' from options
                            other_nodes = [n for n in known_nodes if n['id'] != 'root_me']
                            other_node_names = [n['name'] for n in other_nodes]
                            
                            selected_contacts = st.multiselect(
                                "Who else does this person know?",
                                other_node_names,
                                key=f"multi_{i}"
                            )
                            
                            for contact_name in selected_contacts:
                                contact_id = node_options[contact_name]
                                rel_label = st.text_input(f"Relation to {contact_name}", value="Friend", key=f"rel_{i}_{contact_id}")
                                manual_connections.append({
                                    "target_id": contact_id,
                                    "label": rel_label
                                })

                    decisions.append({
                        "index": i,
                        "choice": choice,
                        "new_name": name_input,
                        "existing_name": existing_select,
                        "description": desc,
                        "relation_input": relation_input,
                        "connect_to_me": connect_to_me,
                        "manual_connections": manual_connections
                    })
                
                commit = st.form_submit_button("Commit to Memory")
                
                if commit:
                    related_node_ids = []
                    
                    # 1. Process Nodes
                    for d in decisions:
                        choice = d['choice']
                        final_id = None
                        
                        if choice == "Ignore": continue
                        
                        if "New Person" in choice:
                            if d['new_name']:
                                new_id = str(uuid.uuid4())
                                
                                # Auto-save avatar if available
                                detected_person = st.session_state.detected_people[d['index']]
                                if 'cropped_face' in detected_person:
                                    try:
                                        avatar_dir = os.path.join("assets", "avatars")
                                        if not os.path.exists(avatar_dir): os.makedirs(avatar_dir)
                                        
                                        avatar_path = os.path.join(avatar_dir, f"{new_id}.png")
                                        detected_person['cropped_face'].save(avatar_path, format="PNG")
                                    except Exception as e:
                                        print(f"Failed to save avatar: {e}")

                                new_node = {
                                    "id": new_id,
                                    "name": d['new_name'],
                                    "type": "person",
                                    "description": d['description'], 
                                    "created_at": str(datetime.date.today()),
                                    "avatar_type": "image" # Default to image
                                }
                                data_manager.save_node(new_node)
                                final_id = new_id
                                
                                # Handle Manual Connections
                                # A. Connect to Me
                                if d['connect_to_me']:
                                    related_node_ids.append("root_me")
                                    rel_label = d['relation_input'] if d['relation_input'] else "Friend"
                                    data_manager.add_edge("root_me", final_id, rel_label)
                                
                                # B. Connect to Others
                                for conn in d['manual_connections']:
                                    data_manager.add_edge(final_id, conn['target_id'], conn['label'])
                                    
                        elif "Select Existing" in choice:
                            if d['existing_name']:
                                final_id = node_options[d['existing_name']]
                                related_node_ids.append("root_me") # Default behavior for existing? Or should we check?
                                # Let's assume mentioning existing person implies connection to me for this event context
                                if d['relation_input']:
                                    data_manager.update_edge_attribute("root_me", final_id, "relation_type", d['relation_input'])
                        
                        if final_id:
                            related_node_ids.append(final_id)
                    
                    # Ensure root_me is in related_node_ids if valid (deduplicate)
                    # Actually, update_edges_from_events uses "root_me" implicitly?
                    # Let's clean up related_node_ids
                    final_related_ids = list(set(related_node_ids))
                    if "root_me" not in final_related_ids:
                         # If no one chose 'connect to me', but we usually want the event linked to me?
                         # The requirement was about graph edges. Event participation is separate.
                         # We'll keep 'root_me' in event if ANYONE connected to me, or if it's my memory.
                         # For now, let's always add root_me to event, but edge creation depends on flag.
                         final_related_ids.append("root_me")
                    
                    # 3. Save Event
                    image_list = []
                    if st.session_state.current_image_path:
                        image_list.append(st.session_state.current_image_path)
                        
                    form_data = st.session_state.form_data
                    evt_title = form_data.get('title') if form_data.get('title') else f"{form_data['date']} Memory"
                    
                    new_event = {
                        "id": str(uuid.uuid4()),
                        "title": evt_title,
                        "date": form_data['date'],
                        "content": form_data['content'],
                        "journal_text": form_data['content'],
                        "images": image_list,
                        "related_nodes": list(set(related_node_ids))
                    }
                    data_manager.save_event(new_event)
                    
                    st.success("Memory Crystallized.")
                    st.session_state.step = 'input'
                    st.session_state.detected_people = []
                    st.session_state.current_image_path = None
                    st.rerun()

# --- View: Memory Gallery ---
elif mode == "Memory Gallery":
    st.title("Memory Gallery")
    st.markdown("Review and curate your collected moments.")
    
    events = data_manager.get_all_events()
    
    # View Toggle
    view_mode = st.radio("View Mode", ["List", "Grid"], horizontal=True, label_visibility="collapsed")
    
    if not events:
        st.info("No memories found. Go to 'Time Capsule' to add some!")
    else:
        if view_mode == "Grid":
            # GRID VIEW
            cols = st.columns(3)
            for index, evt in enumerate(events):
                with cols[index % 3]:
                    with st.container(border=True):
                        # Show Image (First one if available)
                        if evt.get('images'):
                            img_path = evt['images'][0]
                            if os.path.exists(img_path):
                                st.image(img_path, use_container_width=True)
                        else:
                            # Placeholder or just skip
                            st.caption("No Image")

                        st.subheader(evt.get('title', 'Untitled'))
                        st.caption(f"📅 {evt.get('date', 'Unknown Date')}")
                        
        else:
            # LIST VIEW
            for evt in events:
                # Create a card for each event
                with st.container(border=True):
                    col_view, col_edit = st.columns([5, 1])
                    
                    with col_edit:
                        is_editing = st.checkbox("Edit", key=f"edit_toggle_{evt['id']}")
                    
                    with col_view:
                        if not is_editing:
                            # READ MODE
                            st.subheader(f"{evt.get('title', 'Untitled Memory')}")
                            st.caption(f"📅 {evt.get('date', 'Unknown Date')}")
                            
                            # Show participants names roughly?
                            # This would require fetching node names. For speed, maybe just IDs or skip.
                            # Skipping for clean gallery view.
                            
                            st.write(evt.get('content', ''))
                            
                            if evt.get('images'):
                                # Display thumbnails
                                cols = st.columns(len(evt['images']))
                                for idx, img_path in enumerate(evt['images']):
                                    if os.path.exists(img_path):
                                        with cols[idx]:
                                            st.image(img_path, use_container_width=True)
                        else:
                            # EDIT MODE
                            st.markdown(f"**Editing: {evt.get('title', 'Untitled')}**")
                            
                            with st.form(key=f"edit_form_{evt['id']}"):
                                new_title = st.text_input("Title", value=evt.get('title', ''))
                                new_date = st.date_input("Date", 
                                    datetime.datetime.strptime(evt.get('date'), '%Y-%m-%d').date() if evt.get('date') else datetime.date.today()
                                )
                                new_content = st.text_area("Journal", value=evt.get('content', ''))
                                
                                # Image replacement (optional implementation, for now let's just keep logic simple)
                                # st.file_uploader... handling image replacement is complex (delete old? keep both?). 
                                # Let's skip file upload in edit for MVP Phase 13 unless strictly required. 
                                # Prompt says: "st.file_uploader('Replace Image')".
                                new_image = st.file_uploader("Replace Image", type=['jpg', 'png'], key=f"up_{evt['id']}")
                                
                                col_save, col_del = st.columns(2)
                                with col_save:
                                    save_btn = st.form_submit_button("💾 Save Changes")
                                with col_del:
                                    del_btn = st.form_submit_button("🗑️ Delete Event", type="primary")
                                
                                if save_btn:
                                    updates = {
                                        "title": new_title,
                                        "date": str(new_date),
                                        "content": new_content,
                                        "journal_text": new_content # Sync alias
                                    }
                                    
                                    if new_image:
                                        # Save new image
                                        assets_dir = os.path.join("assets")
                                        if not os.path.exists(assets_dir): os.makedirs(assets_dir)
                                        file_ext = new_image.name.split('.')[-1]
                                        filename = f"{uuid.uuid4()}.{file_ext}"
                                        filepath = os.path.join(assets_dir, filename)
                                        with open(filepath, "wb") as f:
                                            f.write(new_image.getbuffer())
                                        
                                        updates["images"] = [filepath] # Replace strategy
                                        
                                    data_manager.update_event(evt['id'], updates)
                                    st.success("Updated!")
                                    st.rerun()
                                    
                                if del_btn:
                                    data_manager.delete_event(evt['id'])
                                    st.warning("Deleted!")
                                    st.rerun()
