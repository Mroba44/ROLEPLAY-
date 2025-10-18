import discord
from discord.ext import commands
from flask import Flask, request, jsonify
import requests
import json
import asyncio
from threading import Thread

# Bot Configuration
DISCORD_TOKEN = "YOUR_DISCORD_BOT_TOKEN"
GITHUB_WEBHOOK_SECRET = "your_webhook_secret"  # Optional but recommended
CHANNEL_ID = 123456789012345678  # Your Discord channel ID

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Flask app for GitHub webhooks
app = Flask(__name__)

class GitHubBot:
    def __init__(self):
        self.bot = bot
        self.channel = None
    
    async def setup_hook(self):
        """Setup channel when bot is ready"""
        self.channel = self.bot.get_channel(CHANNEL_ID)
        if self.channel:
            print(f"Bot connected to channel: {self.channel.name}")
    
    async def send_embed(self, title, description, color=0x00ff00, fields=None):
        """Send embed message to Discord"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=discord.utils.utcnow()
        )
        
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        
        embed.set_footer(text="GitHub Updates")
        
        if self.channel:
            await self.channel.send(embed=embed)
    
    async def on_github_push(self, payload):
        """Handle GitHub push events"""
        repo_name = payload['repository']['full_name']
        branch = payload['ref'].replace('refs/heads/', '')
        pusher = payload['pusher']['name']
        commits = payload['commits']
        
        if commits:
            latest_commit = commits[0]
            commit_message = latest_commit['message']
            commit_url = latest_commit['url']
            commit_author = latest_commit['author']['name']
            
            # Create embed
            fields = [
                ("Branch", branch, True),
                ("Pushed by", pusher, True),
                ("Commits", str(len(commits)), True),
                ("Latest Commit", f"[{commit_message[:50]}...]({commit_url})", False),
                ("Author", commit_author, True)
            ]
            
            await self.send_embed(
                title=f"🚀 Repository Updated: {repo_name}",
                description=f"New code pushed to **{repo_name}**",
                color=0x3498db,
                fields=fields
            )
            
            # Send detailed commit info if multiple commits
            if len(commits) > 1:
                commit_list = "\n".join([f"• {c['message'][:80]}..." for c in commits[:5]])
                if len(commits) > 5:
                    commit_list += f"\n• ... and {len(commits) - 5} more commits"
                
                await self.send_embed(
                    title="📝 Recent Commits",
                    description=commit_list,
                    color=0xf39c12
                )
    
    async def on_github_pull_request(self, payload):
        """Handle GitHub pull request events"""
        action = payload['action']
        pr = payload['pull_request']
        repo_name = payload['repository']['full_name']
        
        fields = [
            ("PR Title", f"#{pr['number']}: {pr['title']}", False),
            ("Author", pr['user']['login'], True),
            ("Branch", f"{pr['head']['ref']} → {pr['base']['ref']}", True),
            ("State", pr['state'], True)
        ]
        
        await self.send_embed(
            title=f"🔀 Pull Request {action.capitalize()}: {repo_name}",
            description=pr['body'][:200] + "..." if pr['body'] else "No description",
            color=0x9b59b6,
            fields=fields
        )
    
    async def on_github_issues(self, payload):
        """Handle GitHub issue events"""
        action = payload['action']
        issue = payload['issue']
        repo_name = payload['repository']['full_name']
        
        color = {
            'opened': 0xe74c3c,
            'closed': 0x2ecc71,
            'reopened': 0xf39c12
        }.get(action, 0x95a5a6)
        
        fields = [
            ("Issue", f"#{issue['number']}: {issue['title']}", False),
            ("Author", issue['user']['login'], True),
            ("State", issue['state'], True)
        ]
        
        await self.send_embed(
            title=f"🎯 Issue {action.capitalize()}: {repo_name}",
            description=issue['body'][:200] + "..." if issue['body'] else "No description",
            color=color,
            fields=fields
        )

# Create bot instance
github_bot = GitHubBot()

# Discord Bot Events
@bot.event
async def on_ready():
    print(f'🤖 Logged in as {bot.user.name}')
    await github_bot.setup_hook()

# Discord Commands
@bot.command(name='github')
async def github_info(ctx):
    """Show GitHub repository info"""
    embed = discord.Embed(
        title="🔗 GitHub Repository",
        description="Monitor your GitHub repository updates in real-time!",
        color=0x7289da
    )
    
    embed.add_field(
        name="Setup Webhook",
        value="Go to repository settings → Webhooks → Add webhook\nURL: `http://your-server:5000/webhook`",
        inline=False
    )
    
    embed.add_field(
        name="Events",
        value="• Push\n• Pull Requests\n• Issues",
        inline=True
    )
    
    await ctx.send(embed=embed)

@bot.command(name='deploy')
async def deploy_notification(ctx, version=None):
    """Send manual deployment notification"""
    if not version:
        version = "latest"
    
    await github_bot.send_embed(
        title="🚀 Deployment Started",
        description=f"Deploying version **{version}** to server",
        color=0xf39c12,
        fields=[
            ("Status", "In Progress", True),
            ("Initiated by", ctx.author.display_name, True)
        ]
    )

# Flask Webhook Routes
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handle GitHub webhook posts"""
    try:
        # Verify webhook secret (optional but recommended)
        # signature = request.headers.get('X-Hub-Signature-256')
        # if not verify_signature(signature, request.data):
        #     return jsonify({'status': 'unauthorized'}), 401
        
        event_type = request.headers.get('X-GitHub-Event')
        payload = request.json
        
        # Process event in Discord bot
        asyncio.run_coroutine_threadsafe(
            process_github_event(event_type, payload), 
            bot.loop
        )
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'status': 'error'}), 500

async def process_github_event(event_type, payload):
    """Process GitHub events and send to Discord"""
    try:
        if event_type == 'push':
            await github_bot.on_github_push(payload)
        elif event_type == 'pull_request':
            await github_bot.on_github_pull_request(payload)
        elif event_type == 'issues':
            await github_bot.on_github_issues(payload)
        elif event_type == 'ping':
            print("GitHub webhook ping received")
        else:
            print(f"Unhandled event type: {event_type}")
            
    except Exception as e:
        print(f"Error processing event: {e}")

def run_flask():
    """Run Flask webhook server"""
    app.run(host='0.0.0.0', port=5000, debug=False)

def run_bot():
    """Run Discord bot"""
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    # Start Flask webhook server in separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start Discord bot
    run_bot()
