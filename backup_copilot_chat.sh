#!/bin/bash

# GitHub Copilot Chat History Backup Script
# This script creates a comprehensive backup of all GitHub Copilot chat data

# Set backup directory with timestamp
BACKUP_DIR="$HOME/copilot_chat_backup_$(date +%Y%m%d_%H%M%S)"
VSCODE_CONFIG="$HOME/.config/Code"

echo "Creating GitHub Copilot chat backup..."
echo "Backup directory: $BACKUP_DIR"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if VS Code config directory exists
if [ ! -d "$VSCODE_CONFIG" ]; then
    echo "Error: VS Code configuration directory not found at $VSCODE_CONFIG"
    exit 1
fi

# Backup global storage (includes command/setting embeddings and debug data)
echo "Backing up global storage..."
if [ -d "$VSCODE_CONFIG/User/globalStorage/github.copilot-chat" ]; then
    cp -r "$VSCODE_CONFIG/User/globalStorage/github.copilot-chat" "$BACKUP_DIR/globalStorage_copilot-chat"
    echo "✓ Global storage backed up"
else
    echo "⚠ No global copilot-chat storage found"
fi

# Backup all workspace chat sessions
echo "Backing up workspace chat sessions..."
WORKSPACE_STORAGE="$VSCODE_CONFIG/User/workspaceStorage"
CHAT_COUNT=0

if [ -d "$WORKSPACE_STORAGE" ]; then
    mkdir -p "$BACKUP_DIR/workspaceStorage"
    
    # Find all workspace directories with chat data
    for workspace_dir in "$WORKSPACE_STORAGE"/*; do
        if [ -d "$workspace_dir" ]; then
            workspace_id=$(basename "$workspace_dir")
            has_chat_data=false
            
            # Check for chat sessions
            if [ -f "$workspace_dir/chatSessions" ]; then
                mkdir -p "$BACKUP_DIR/workspaceStorage/$workspace_id"
                cp "$workspace_dir/chatSessions" "$BACKUP_DIR/workspaceStorage/$workspace_id/"
                has_chat_data=true
                ((CHAT_COUNT++))
            fi
            
            # Check for chat editing sessions
            if [ -f "$workspace_dir/chatEditingSessions" ]; then
                mkdir -p "$BACKUP_DIR/workspaceStorage/$workspace_id"
                cp "$workspace_dir/chatEditingSessions" "$BACKUP_DIR/workspaceStorage/$workspace_id/"
                has_chat_data=true
            fi
            
            # Check for GitHub copilot-chat specific data
            if [ -d "$workspace_dir/GitHub.copilot-chat" ]; then
                mkdir -p "$BACKUP_DIR/workspaceStorage/$workspace_id"
                cp -r "$workspace_dir/GitHub.copilot-chat" "$BACKUP_DIR/workspaceStorage/$workspace_id/"
                has_chat_data=true
            fi
            
            # Create workspace info file
            if [ "$has_chat_data" = true ]; then
                echo "Workspace ID: $workspace_id" > "$BACKUP_DIR/workspaceStorage/$workspace_id/workspace_info.txt"
                echo "Backup Date: $(date)" >> "$BACKUP_DIR/workspaceStorage/$workspace_id/workspace_info.txt"
                
                # Try to find workspace path if available
                if [ -f "$workspace_dir/meta.json" ]; then
                    echo "Workspace metadata:" >> "$BACKUP_DIR/workspaceStorage/$workspace_id/workspace_info.txt"
                    cat "$workspace_dir/meta.json" >> "$BACKUP_DIR/workspaceStorage/$workspace_id/workspace_info.txt"
                fi
            fi
        fi
    done
    
    echo "✓ Found and backed up $CHAT_COUNT workspace(s) with chat data"
else
    echo "⚠ No workspace storage found"
fi

# Backup VS Code settings that might be relevant
echo "Backing up VS Code settings..."
if [ -f "$VSCODE_CONFIG/User/settings.json" ]; then
    cp "$VSCODE_CONFIG/User/settings.json" "$BACKUP_DIR/vscode_settings.json"
    echo "✓ VS Code settings backed up"
fi

# Create backup summary
echo "Creating backup summary..."
cat > "$BACKUP_DIR/backup_summary.txt" << EOF
GitHub Copilot Chat Backup Summary
==================================
Backup Date: $(date)
Backup Directory: $BACKUP_DIR
VS Code Config Path: $VSCODE_CONFIG

Contents:
- Global Storage: $([ -d "$BACKUP_DIR/globalStorage_copilot-chat" ] && echo "✓ Included" || echo "✗ Not found")
- Workspace Chat Sessions: $CHAT_COUNT workspace(s)
- VS Code Settings: $([ -f "$BACKUP_DIR/vscode_settings.json" ] && echo "✓ Included" || echo "✗ Not found")

Directory Structure:
$(tree "$BACKUP_DIR" 2>/dev/null || find "$BACKUP_DIR" -type f | head -20)

Files backed up:
$(find "$BACKUP_DIR" -type f -exec ls -lh {} \; | wc -l) files
Total backup size: $(du -sh "$BACKUP_DIR" | cut -f1)
EOF

# Create restoration instructions
cat > "$BACKUP_DIR/RESTORE_INSTRUCTIONS.md" << 'EOF'
# How to Restore GitHub Copilot Chat History

## Automatic Restoration (Recommended)

Run the restoration script:
```bash
chmod +x restore_copilot_chat.sh
./restore_copilot_chat.sh
```

## Manual Restoration

1. **Stop VS Code** completely before restoring

2. **Backup current data** (optional but recommended):
   ```bash
   cp -r ~/.config/Code/User/globalStorage/github.copilot-chat ~/.config/Code/User/globalStorage/github.copilot-chat.backup
   ```

3. **Restore global storage**:
   ```bash
   cp -r globalStorage_copilot-chat/* ~/.config/Code/User/globalStorage/github.copilot-chat/
   ```

4. **Restore workspace storage**:
   ```bash
   cp -r workspaceStorage/* ~/.config/Code/User/workspaceStorage/
   ```

5. **Restart VS Code**

## Notes
- Chat history is tied to specific workspace IDs
- Some chats may not appear if the original workspace is no longer available
- Global settings and embeddings will be restored
- Consider backing up current data before restoring
EOF

# Create restoration script
cat > "$BACKUP_DIR/restore_copilot_chat.sh" << 'EOF'
#!/bin/bash

echo "GitHub Copilot Chat History Restoration Script"
echo "=============================================="

# Get the directory where this script is located
BACKUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VSCODE_CONFIG="$HOME/.config/Code"

echo "Backup directory: $BACKUP_DIR"
echo "VS Code config: $VSCODE_CONFIG"

# Check if VS Code is running
if pgrep -f "code" > /dev/null; then
    echo "⚠ WARNING: VS Code appears to be running."
    echo "Please close VS Code completely before restoring chat history."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Restoration cancelled."
        exit 1
    fi
fi

# Create backup of current data
echo "Creating backup of current chat data..."
CURRENT_BACKUP="$HOME/copilot_chat_current_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$CURRENT_BACKUP"

if [ -d "$VSCODE_CONFIG/User/globalStorage/github.copilot-chat" ]; then
    cp -r "$VSCODE_CONFIG/User/globalStorage/github.copilot-chat" "$CURRENT_BACKUP/"
    echo "✓ Current global storage backed up to: $CURRENT_BACKUP"
fi

# Restore global storage
if [ -d "$BACKUP_DIR/globalStorage_copilot-chat" ]; then
    echo "Restoring global storage..."
    mkdir -p "$VSCODE_CONFIG/User/globalStorage"
    cp -r "$BACKUP_DIR/globalStorage_copilot-chat" "$VSCODE_CONFIG/User/globalStorage/github.copilot-chat"
    echo "✓ Global storage restored"
else
    echo "⚠ No global storage found in backup"
fi

# Restore workspace storage
if [ -d "$BACKUP_DIR/workspaceStorage" ]; then
    echo "Restoring workspace storage..."
    for workspace_backup in "$BACKUP_DIR/workspaceStorage"/*; do
        if [ -d "$workspace_backup" ]; then
            workspace_id=$(basename "$workspace_backup")
            target_dir="$VSCODE_CONFIG/User/workspaceStorage/$workspace_id"
            
            echo "Restoring workspace: $workspace_id"
            mkdir -p "$target_dir"
            cp -r "$workspace_backup"/* "$target_dir/"
        fi
    done
    echo "✓ Workspace storage restored"
else
    echo "⚠ No workspace storage found in backup"
fi

echo ""
echo "Restoration completed!"
echo "Current data backed up to: $CURRENT_BACKUP"
echo "Please restart VS Code to see your restored chat history."
EOF

chmod +x "$BACKUP_DIR/restore_copilot_chat.sh"

# Create archive option
echo ""
echo "Creating compressed archive..."
tar -czf "${BACKUP_DIR}.tar.gz" -C "$(dirname "$BACKUP_DIR")" "$(basename "$BACKUP_DIR")"
echo "✓ Compressed backup created: ${BACKUP_DIR}.tar.gz"

echo ""
echo "=========================================="
echo "Backup completed successfully!"
echo "=========================================="
echo "Backup location: $BACKUP_DIR"
echo "Compressed backup: ${BACKUP_DIR}.tar.gz"
echo "Workspaces with chat data: $CHAT_COUNT"
echo ""
echo "To restore chat history:"
echo "1. Extract the backup if using compressed version"
echo "2. Run: cd '$BACKUP_DIR' && ./restore_copilot_chat.sh"
echo "3. Or follow manual instructions in RESTORE_INSTRUCTIONS.md"
echo ""
echo "Total backup size: $(du -sh "$BACKUP_DIR" | cut -f1)"
