import sqlite3
import json

def analyze_investigation():
    print('=== AI AGENT INVESTIGATION ANALYSIS ===')
    print()
    
    # Check memory tree
    print('🌳 MEMORY TREE ANALYSIS:')
    conn = sqlite3.connect('investigation_20250523_120736.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, data FROM nodes')
    nodes = cursor.fetchall()
    
    print(f'Total nodes built: {len(nodes)}')
    print()
    
    # Show key findings
    print('🔍 KEY FINDINGS DISCOVERED:')
    for node_id, data_json in nodes:
        data = json.loads(data_json)
        name = data['name']
        desc = data['description']
        
        if 'Hartwell' in name and 'Suspect' in name:
            print(f'🎯 PRIMARY SUSPECT: {desc[:100]}...')
        elif 'Robert' in name and 'Timeline' in name:
            print(f'⏰ TIMELINE ISSUE: {desc[:100]}...')
        elif 'Staged' in name:
            print(f'🎭 CRIME SCENE: {desc[:100]}...')
        elif 'Proof' in name and 'Motive' in name:
            print(f'💡 MOTIVE: {desc[:100]}...')
    
    conn.close()
    
    print()
    print('📋 TASK EXECUTION SUMMARY:')
    
    # Check tasks
    conn = sqlite3.connect('tasks_20250523_120736.db')
    cursor = conn.cursor()
    cursor.execute('SELECT data FROM tasks')
    tasks = cursor.fetchall()
    
    completed = sum(1 for (data_json,) in tasks if json.loads(data_json)['status'] == 'completed')
    pending = len(tasks) - completed
    
    print(f'• Total tasks created: {len(tasks)}')
    print(f'• Tasks completed: {completed}')
    print(f'• Tasks pending: {pending}')
    
    # Show completed tasks
    print()
    print('✅ COMPLETED INVESTIGATIVE TASKS:')
    for (data_json,) in tasks:
        data = json.loads(data_json)
        if data['status'] == 'completed':
            print(f'• {data["description"][:80]}...')
    
    conn.close()

if __name__ == "__main__":
    analyze_investigation() 