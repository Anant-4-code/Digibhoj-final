import re

path = 'backend/templates/provider/analytics.html'
content = open(path, encoding='utf-8').read()

old = '<h1>Analytics &amp; Reports</h1>'
new = '''<h1 style="display:flex;align-items:center;gap:12px">Analytics &amp; Reports
          <span id="live-refresh-badge" style="font-size:11px;font-weight:700;background:rgba(8,201,82,0.15);color:var(--green);padding:3px 10px;border-radius:20px;letter-spacing:0.5px;display:inline-flex;align-items:center;gap:6px">
            <span style="width:6px;height:6px;border-radius:50%;background:var(--green);display:inline-block;animation:livePulse 1.5s infinite"></span>
            Live
          </span>
        </h1>'''

if old in content:
    content = content.replace(old, new, 1)
    
    # Also add livePulse keyframes to the style section
    style_target = '.stats-grid .stat-card {'
    style_new = '''@keyframes livePulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(1.4); }
  100% { opacity: 1; transform: scale(1); }
}
''' + style_target
    content = content.replace(style_target, style_new, 1)
    
    # Update subtitle too
    old_p = '<p>Track your business performance and insights</p>'
    new_p = '<p>Real-time analytics &mdash; auto-refreshes every 30 seconds</p>'
    content = content.replace(old_p, new_p, 1)
    
    open(path, 'w', encoding='utf-8').write(content)
    print('SUCCESS: Analytics header patched!')
else:
    print('NOT FOUND')
    # Debug: show what's there
    idx = content.find('Analytics')
    print(repr(content[idx-50:idx+100]))
