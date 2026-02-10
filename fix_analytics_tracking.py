#!/usr/bin/env python3
"""
Script to fix analytics tracking in bot_webhook.py
Removes track_command(success=False) from input validation blocks
"""
import re

print("🔧 Fixing analytics tracking...")

with open('backend/bot_webhook.py', 'r', encoding='utf-8') as f:
    content = f.read()

original_lines = len(content.splitlines())

# Pattern pour identifier les blocs de validation d'input à corriger
# Ces blocs ont un reply_text avec un message d'aide, suivi d'un track_command avec success=False

# Patterns à supprimer (VALIDATIONS INPUT ONLY)
patterns_to_remove = [
    # analyze_command - missing text
    r"\s+# Track failed command\n\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('analyze', user_id, success=False, error='missing_text'\)\n\s+return",
    
    # add_command - invalid args
    r"\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('add', user_id, success=False, error='invalid_args'\)\n\s+return",
    
    # add_command - invalid numbers
    r"\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('add', user_id, success=False, error='invalid_numbers'\)\n\s+return",
    
    # add_command - negative values
    r"\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('add', user_id, success=False, error='negative_values'\)\n\s+return",
    
    # remove_command - invalid args
    r"\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('remove', user_id, success=False, error='invalid_args'\)\n\s+return",
    
    # remove_command - negative quantity
    r"\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('remove', user_id, success=False, error='negative_quantity'\)\n\s+return",
    
    # remove_command - invalid quantity
    r"\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('remove', user_id, success=False, error='invalid_quantity'\)\n\s+return",
    
    # sell_command - invalid args
    r"\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('sell', user_id, success=False, error='invalid_args'\)\n\s+return",
    
    # sell_command - invalid numbers  
    r"\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('sell', user_id, success=False, error='invalid_numbers'\)\n\s+return",
    
    # sell_command - negative values
    r"\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('sell', user_id, success=False, error='negative_values'\)\n\s+return",
    
    # setalert_command - invalid args
    r"\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('setalert', user_id, success=False, error='invalid_args'\)\n\s+return",
    
    # setalert_command - invalid alert type
    r"\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('setalert', user_id, success=False, error='invalid_alert_type'\)\n\s+return",
    
    # setalert_command - invalid price
    r"\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('setalert', user_id, success=False, error='invalid_price'\)\n\s+return",
    
    # setalert_command - negative price
    r"\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('setalert', user_id, success=False, error='negative_price'\)\n\s+return",
    
    # setalert_command - unsupported symbol
    r"\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('setalert', user_id, success=False, error='unsupported_symbol'\)\n\s+return",
    
    # removealert_command - invalid args
    r"\s+if ANALYTICS_AVAILABLE:\n\s+track_command\('removealert', user_id, success=False, error='invalid_args'\)\n\s+return",
]

fixed_content = content
removals = 0

for pattern in patterns_to_remove:
    matches = re.findall(pattern, fixed_content)
    if matches:
        removals += len(matches)
        fixed_content = re.sub(pattern, "\n        return", fixed_content)

fixed_lines = len(fixed_content.splitlines())

print(f"✅ Fixed! Removed {removals} incorrect tracking calls")
print(f"   Lines: {original_lines} → {fixed_lines} (−{original_lines - fixed_lines})")

with open('backend/bot_webhook.py', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("✅ backend/bot_webhook.py updated")
print("\n📊 RESULT:")
print("   ❌ Input validations: NO LONGER tracked as errors")
print("   ✅ Real exceptions: STILL tracked in except blocks")
print("   ✅ Success cases: STILL tracked")
print("\n🎯 Expected error rate after deploy: <5% (down from 20%)")
