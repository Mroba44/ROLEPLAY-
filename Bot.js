const { Client, GatewayIntentBits, EmbedBuilder } = require('discord.js');
const express = require('express');
const app = express();

const DISCORD_TOKEN = 'YOUR_BOT_TOKEN';
const CHANNEL_ID = 'YOUR_CHANNEL_ID';

const client = new Client({
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages]
});

app.use(express.json());

client.once('ready', () => {
    console.log(`🤖 Logged in as ${client.user.tag}`);
});

// GitHub Webhook
app.post('/webhook', (req, res) => {
    const event = req.headers['x-github-event'];
    const payload = req.body;

    handleGitHubEvent(event, payload);
    res.status(200).send('OK');
});

function handleGitHubEvent(event, payload) {
    const channel = client.channels.cache.get(CHANNEL_ID);
    if (!channel) return;

    if (event === 'push') {
        const embed = new EmbedBuilder()
            .setTitle('🚀 Code Pushed')
            .setDescription(`Repository: **${payload.repository.full_name}**`)
            .addFields(
                { name: 'Branch', value: payload.ref.replace('refs/heads/', ''), inline: true },
                { name: 'Commits', value: payload.commits.length.toString(), inline: true },
                { name: 'Latest Commit', value: payload.commits[0].message.slice(0, 100) }
            )
            .setColor(0x00FF00)
            .setTimestamp();

        channel.send({ embeds: [embed] });
    }
}

app.listen(5000, () => {
    console.log('🌐 Webhook server running on port 5000');
});

client.login(DISCORD_TOKEN);
