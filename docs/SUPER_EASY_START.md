# 🚀 CAB Super Easy Start Guide

> **Get CAB running in 5 minutes or less!**

## 🎯 For Complete Beginners

### Option 1: One-Command Setup (Easiest)
```bash
# Clone and run everything automatically
git clone https://github.com/your-org/CodeAssistBench.git
cd CodeAssistBench
python super_easy_setup.py
```

### Option 2: Docker (No Python Setup Required)
```bash
# Clone and run with Docker
git clone https://github.com/your-org/CodeAssistBench.git
cd CodeAssistBench
docker-compose up
```

### Option 3: Try It First (No Setup Required)
```bash
# Just see what CAB can do
python try_cab.py
```

## 🎮 For Researchers

### Quick Test (2 minutes)
```bash
# Test with mock agent (no API keys needed)
python test_agent.py --agent mock --dataset data/converted_dataset.jsonl --max-issues 1
```

### Test Your AI Model (5 minutes)
```bash
# Test with your preferred AI tool
python test_agent.py --agent cursor-cli --dataset data/converted_dataset.jsonl --max-issues 3
```

## 🔧 For Developers

### Add Your Custom Agent (10 minutes)
```bash
# Create your agent
python create_my_agent.py

# Test it
python test_custom_agent.py my_agent.py MyAgent
```

## 📊 For Evaluators

### Compare Multiple AI Models
```bash
# Test multiple agents
python compare_agents.py --agents mock,cursor-cli,amazon-q --max-issues 5
```

### Use Different Judges
```bash
# Test with different judges
python test_judge_agents.py
```

## 🎯 What You Get

- ✅ **Working CAB**: Fully functional benchmark
- ✅ **Sample Data**: Pre-loaded test issues
- ✅ **Multiple Agents**: Mock, Cursor CLI, Amazon Q, etc.
- ✅ **Multiple Judges**: Different AI models for evaluation
- ✅ **Clear Results**: Easy-to-understand performance metrics

## 🆘 Need Help?

1. **Quick Questions**: Check `FAQ.md`
2. **Detailed Guide**: Read `README.md`
3. **Custom Agents**: See `CUSTOM_AGENT_GUIDE.md`
4. **Issues**: Open a GitHub issue

## 🎉 Success!

If you see this, CAB is working:
```
🎯 Evaluation Results for MockAgent
============================================================
📊 Total Issues: 1
✅ Successful: 1
❌ Failed: 0
📈 Satisfaction Rate: 100.00%
🔄 Average Rounds: 1.0
⏱️  Average Duration: 0.1s
```

**You're ready to benchmark AI coding assistants!** 🚀
