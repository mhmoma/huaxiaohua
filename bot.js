// 引入 discord.js 库
const { Client, GatewayIntentBits } = require('discord.js');
// 引入 dotenv 用于从 .env 文件加载环境变量
require('dotenv').config();

// 创建一个新的客户端实例
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
});

// 当客户端准备好时，这个事件会被触发
client.once('ready', () => {
  console.log(`以 ${client.user.tag} 身份登录!`);
});

// 当收到消息时，这个事件会被触发
client.on('messageCreate', message => {
  // 如果消息是 "ping"
  if (message.content === 'ping') {
    // 回复 "pong"
    message.reply('pong');
  }
});

// 使用 .env 文件中的令牌登录到 Discord
client.login(process.env.DISCORD_TOKEN);
