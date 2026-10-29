import json
with open(r'C:\Users\DAZA\.gemini\antigravity\brain\c67fc3d9-7d86-45c3-be1e-f3bc737860c0\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if i in range(1048, 1070):
            d = json.loads(line)
            st = d.get('step_index')
            tp = d.get('type')
            tc = d.get('tool_calls', [])
            cnt = d.get('content', '')
            print(f"i={i} step={st} tp={tp}")
            if tc:
                for c in tc:
                    print("  TC:", c.get("name"), c.get("args"))
            if cnt:
                print("  CNT:", cnt[:300].replace('\n', ' '))
