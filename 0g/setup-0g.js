import { ethers } from 'ethers';
import { createZGComputeNetworkBroker } from '@0glabs/0g-serving-broker';
import dotenv from 'dotenv';
import { writeFileSync } from 'fs';

// Load environment variables
dotenv.config();

async function setup0GCompute() {
  console.log('🚀 Arsenal Scout AI - 0G Compute Setup\n');

  try {
    // Initialize wallet and provider
    console.log('1️⃣ Connecting to 0G Testnet...');
    const provider = new ethers.JsonRpcProvider('https://evmrpc-testnet.0g.ai');
    const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);

    console.log(`   Wallet Address: ${wallet.address}`);

    // Check balance
    const balance = await provider.getBalance(wallet.address);
    console.log(`   Balance: ${ethers.formatEther(balance)} 0G\n`);

    if (balance === 0n) {
      console.log('⚠️  Warning: Wallet has 0 balance. Get testnet tokens from faucet:');
      console.log('   https://faucet.0g.ai\n');
    }

    // Create broker
    console.log('2️⃣ Initializing 0G Compute Broker...');
    const broker = await createZGComputeNetworkBroker(wallet);
    console.log('   ✅ Broker initialized\n');

    // List available services
    console.log('3️⃣ Discovering AI services...');
    const services = await broker.inference.listService();

    if (services.length === 0) {
      console.log('   ⚠️  No services found. Network may be unavailable.\n');
      return;
    }

    console.log(`   Found ${services.length} service(s):\n`);

    // Display first few services
    const displayServices = services.slice(0, 3);
    for (const service of displayServices) {
      console.log(`   📍 Provider: ${service.provider}`);
      console.log(`      Name: ${service.name}`);
      console.log(`      Model: ${service.model}`);
      console.log(`      URL: ${service.url}\n`);
    }

    // Select first service
    const selectedService = services[0];
    const providerAddress = selectedService.provider;

    console.log(`4️⃣ Selected Service: ${selectedService.name}`);
    console.log(`   Provider: ${providerAddress}\n`);

    // Check if we need to deposit funds
    console.log('5️⃣ Checking account balance...');
    try {
      const account = await broker.ledger.getAccount(wallet.address);
      console.log(`   Main Account Balance: ${ethers.formatEther(account.balance)} 0G\n`);

      if (account.balance === 0n && balance > 0n) {
        console.log('6️⃣ Depositing initial funds (10 0G)...');
        await broker.ledger.depositFund('10');
        console.log('   ✅ Funds deposited\n');
      }
    } catch (error) {
      console.log('   No existing account, will create on first deposit\n');
    }

    // Acknowledge provider
    console.log('7️⃣ Acknowledging provider...');
    try {
      await broker.inference.acknowledgeProviderSigner(providerAddress);
      console.log('   ✅ Provider acknowledged\n');
    } catch (error) {
      console.log(`   ℹ️  ${error.message}\n`);
    }

    // Get service metadata
    console.log('8️⃣ Getting service endpoint...');
    const metadata = await broker.inference.getServiceMetadata(providerAddress);
    console.log(`   Endpoint: ${metadata.endpoint}`);
    console.log(`   Model: ${metadata.model}\n`);

    // Get request headers (contains API key)
    console.log('9️⃣ Generating API credentials...');
    const headers = await broker.inference.getRequestHeaders(providerAddress);

    console.log('   ✅ Credentials generated!\n');

    // Update .env file
    console.log('🔟 Updating .env file...');

    const envContent = `# REQUIRED - Your wallet private key (without 0x prefix)
PRIVATE_KEY=${process.env.PRIVATE_KEY}

# Server config
PORT=${process.env.PORT || 4000}
NODE_ENV=${process.env.NODE_ENV || 'development'}

# 0G Compute AI Credentials (AUTO-GENERATED)
ZG_COMPUTE_ENDPOINT=${metadata.endpoint}
ZG_COMPUTE_MODEL=${metadata.model}
ZG_COMPUTE_PROVIDER=${providerAddress}

# Flask secret key
FLASK_SECRET_KEY=${process.env.FLASK_SECRET_KEY || 'arsenal-scout-ai-hackathon-secret-2024'}
`;

    writeFileSync('.env', envContent);
    console.log('   ✅ .env updated with 0G credentials\n');

    // Save configuration for Flask app
    const config = {
      endpoint: metadata.endpoint,
      model: metadata.model,
      provider: providerAddress,
      service_name: selectedService.name,
      headers: headers
    };

    writeFileSync('0g-config.json', JSON.stringify(config, null, 2));
    console.log('   ✅ Saved 0g-config.json\n');

    console.log('✅ Setup Complete!\n');
    console.log('📝 Next steps:');
    console.log('   1. Your .env file has been updated');
    console.log('   2. Run: pip install -r requirements.txt');
    console.log('   3. Run: python app.py');
    console.log('   4. Open: http://localhost:5000\n');

  } catch (error) {
    console.error('❌ Setup failed:', error.message);
    console.error('\nTroubleshooting:');
    console.error('1. Ensure PRIVATE_KEY is set in .env (without 0x prefix)');
    console.error('2. Get testnet tokens: https://faucet.0g.ai');
    console.error('3. Check network status: https://docs.0g.ai\n');
    process.exit(1);
  }
}

setup0GCompute();
