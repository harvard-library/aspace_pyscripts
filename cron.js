const Cron = require("croner");
const fs = require("fs");
const {spawn} = require("child_process");


/*    ┌──────────────── (optional) second (0 - 59)
      │ ┌────────────── minute (0 - 59)
      │ │ ┌──────────── hour (0 - 23)
      │ │ │ ┌────────── day of month (1 - 31)
      │ │ │ │ ┌──────── month (1 - 12, JAN-DEC)
      │ │ │ │ │ ┌────── day of week (0 - 6, SUN-Mon)
      │ │ │ │ │ │       (0 to 6 are Sunday to Saturday; 7 is Sunday, the same as 0)
      │ │ │ │ │ │       */
Cron("0 0 * * * *", {}, ()=> {
  console.log("running pdfStorer.py");
  let args = ["-t", "dave_mayo@harvard.edu",
              "-f", "dave_mayo@harvard.edu"];
  if (process.env.PDF_TIMEOUT) {
    args.push("--timeout", process.env.PDF_TIMEOUT);
  }

  try {
    if ( !fs.existsSync("/aspace_pyscripts/pdfstorerdaemon.pid") ) {
      subprocess = spawn("/aspace_pyscripts/pdfStorer.py",
                         args);
      subprocess.stdout.on('data', (data) => { console.log(data) });
      subprocess.stderr.on('data', (data) => { console.log("ERR: " + data) });
    }
  }
  catch (e) {
    console.log(e);
  }
});
