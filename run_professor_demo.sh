#!/bin/bash
# Professor Demo Script - Easy to run visual demonstration

echo "🎓 Vector Clock Emergency System - Professor Demo"
echo "==============================================="
echo ""
echo "This will run a comprehensive visual demonstration showing:"
echo "✅ Vector clock synchronization"
echo "✅ Emergency prioritization"  
echo "✅ Message priority handling"
echo "✅ Network emergency response"
echo ""
echo "Press Enter to start the demonstration..."
read

# Change to project directory and run the visual demo
cd "/home/sina/Desktop/Related Work/pr/ma-sinafadavi"
PYTHONPATH=. "/home/sina/Desktop/Related Work/pr/ma-sinafadavi/.venv/bin/python" rec/replication/visual_demo.py
