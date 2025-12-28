import base64
import os
import networkx as nx
from streamlit_agraph import Node, Edge, Config

def image_to_base64(image_path):
    if not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as img_file:
        return "data:image/png;base64," + base64.b64encode(img_file.read()).decode('utf-8')

def get_graph_data(nodes_data, edges_data, center_node_id=None, k_hop=1, seed=42):
    """
    Converts raw data into agraph Node/Edge objects using NetworkX for filtering.
    If center_node_id is set, returns a K-Hop subgraph.
    """
    # 1. Build NetworkX Graph
    G = nx.Graph()
    
    # Add nodes with attributes
    for n in nodes_data:
        G.add_node(n['id'], **n)
        
    # Add edges with attributes
    for e in edges_data:
        G.add_edge(e['source'], e['target'], **e)
        
    # 2. Filter Subgraph (K-Hop)
    if center_node_id:
        if center_node_id in G:
            G = nx.ego_graph(G, center_node_id, radius=k_hop)
        else:
            # Fallback if center node not found (e.g. deleted)
            pass
            
    nodes = []
    edges = []
    
    # 3. Create agraph Nodes
    for node_id, n in G.nodes(data=True):
        is_me = (node_id == "root_me")
        
        # Tooltip content
        title_text = n.get('name', 'Unknown')
        if n.get('description'):
            title_text += f"\n{n['description']}"
            
        # Avatar Logic - Galaxy Theme
        avatar_type = n.get("avatar_type", "image")
        
        # Default Galaxy Styles (Type A: Star)
        node_shape = "dot" 
        node_image = None
        node_color = "#FFFFFF" # 恒星亮色
        node_size = 30 # 恒星大小
        node_shadow = {
            "enabled": True, 
            "color": "rgba(255, 255, 0, 0.8)", # 强烈的金黄色光晕
            "size": 30, 
            "x": 0, "y": 0
        }
        
        # Check for avatar image
        avatar_path = os.path.join("assets", "avatars", f"{node_id}.png")
        has_avatar = False
        if avatar_type == "image" and os.path.exists(avatar_path):
            has_avatar = True
            b64_img = image_to_base64(avatar_path)
            if b64_img:
                node_shape = "circularImage"
                node_image = b64_img
                # Type B: Planet (with Avatar)
                node_shadow = {
                    "enabled": True,
                    "color": "rgba(135, 206, 250, 0.6)", # 柔和的天蓝色光晕 (大气层)
                    "size": 15,
                    "x": 0, "y": 0
                }
        
        # Refine Star Logic if no avatar
        if not has_avatar:
            if is_me:
                node_size = 40 # Me 节点稍大
                # Keep golden glow
            else:
                # Other stars
                node_color = n.get("avatar_value", "#FFFFFF")
        
        nodes.append(Node(
            id=node_id,
            label=n.get('name', 'Unknown'),
            title=title_text,
            size=node_size,
            color=node_color,
            shape=node_shape,
            image=node_image if node_image else "",
            borderWidth=0, # 无边框
            shadow=node_shadow,
            font={"color": "#f0f0f0", "size": 14, "face": "Courier New"} # 白色字体
        ))
        
    # 4. Create agraph Edges
    for u, v, e in G.edges(data=True):
        edge_label = e.get("relation_type", "")
        
        if center_node_id and k_hop == 1:
            if u != center_node_id and v != center_node_id:
                continue
                
        edges.append(Edge(
            source=u,
            target=v,
            label=edge_label,
            color={'color': 'rgba(255, 255, 255, 0.15)', 'highlight': '#80dfff'}, # 微弱白线
            smooth={'type': 'continuous'},
            strokeWidth=1,
            font={"size": 10, "color": "#888", "align": "middle", "strokeWidth": 0}
        ))
        
    physics = {
        "enabled": True,
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {
            "theta": 0.5,
            "gravitationalConstant": -100, 
            "centralGravity": 0.01,
            "springConstant": 0.05,
            "springLength": 150,           
            "damping": 0.4,
            "avoidOverlap": 1
        },
        "stabilization": {
            "enabled": True,
            "iterations": 200,             
            "updateInterval": 25
        }
    }

    interaction = {
        "dragNodes": True,
        "dragView": True,
        "zoomView": True,
        "hover": True,
        "navigationButtons": False,
        "tooltipDelay": 200
    }

    config = Config(
        width="100%",
        height=600,
        directed=False,
        physics=physics, 
        interaction=interaction,
        hierarchical=False,
        fit=True,
        layout={'randomSeed': seed},
        nodeHighlightBehavior=True,
        highlightColor="#FFD700", 
        collapsible=False,
        heading="", 
        backgroundColor="#00000000" # 全透明背景
    )
    
    return nodes, edges, config
