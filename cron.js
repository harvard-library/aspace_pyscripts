const Cron = require("croner");
const fs = require("fs");
const {spawn} = require("child_process");

Cron("*/5 * * * * *", {}, ()=> {
  console.log("running pdfStorer.py");
  try {
    if ( !fs.existsSync("/aspace_pyscripts/pdfstorerdaemon.pid") ) {
      subprocess = spawn("/aspace_pyscripts/pdfStorer.py",
                         ["-t", "dave_mayo@harvard.edu",
                          "-f", "dave_mayo@harvard.edu"]);
      subprocess.stdout.on('data', (data) => { console.log(data) });
      subprocess.stderr.on('data', (data) => { console.log("ERR: " + data) });
    }
  }
  catch (e) {
    console.log(e);
  }
});
