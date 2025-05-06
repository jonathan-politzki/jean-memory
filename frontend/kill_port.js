const { execSync } = require('child_process');

// Ports to clean up
const ports = [3000, 3001, 3002, 3003, 8000, 8080];

// Kill processes on all specified ports
ports.forEach(port => {
  try {
    console.log(`Finding processes on port ${port}...`);
    
    // Find PIDs using the port
    const findCommand = `lsof -i :${port} -t`;
    
    try {
      const pids = execSync(findCommand, { encoding: 'utf8' }).trim().split('\n');
      
      if (pids.length === 0 || (pids.length === 1 && pids[0] === '')) {
        console.log(`No process found using port ${port}`);
        return;
      }
      
      // Kill each PID found
      pids.forEach(pid => {
        if (pid) {
          console.log(`Killing process ${pid} on port ${port}`);
          try {
            execSync(`kill -9 ${pid}`);
            console.log(`Successfully killed process ${pid}`);
          } catch (killError) {
            console.error(`Error killing process ${pid}: ${killError.message}`);
          }
        }
      });
    } catch (error) {
      // lsof will exit with code 1 if no processes found, which is not an error for us
      if (!error.message.includes('Command failed')) {
        console.error(`Error finding processes on port ${port}: ${error.message}`);
      } else {
        console.log(`No process found using port ${port}`);
      }
    }
  } catch (error) {
    console.error(`Error processing port ${port}: ${error.message}`);
  }
}); 