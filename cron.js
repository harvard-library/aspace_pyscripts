const Cron = require("croner");
const {spawn} = require("child_process");

Cron("* */20 * * * *", {}, ()=> {
  console.log("running pdfStorer.py");
  try {
    subprocess = spawn("/aspace_pyscripts/pdfStorer.py",
                       ["-t", "dave_mayo@harvard.edu",
                        "-f", "dave_mayo@harvard.edu"]);
    subprocess.stdout.on('data', (data) => { console.log(data) });
    subprocess.stderr.on('data', (data) => { console.log("ERR: " + data) });
  }
  catch (e) {
    console.log(e);
  }
});
