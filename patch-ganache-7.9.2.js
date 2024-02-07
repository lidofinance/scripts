/**
 * Ganache v7.9.2 patch for JSON.stringify issue
 * This fixes reading a lot of events events from debug_traceTransaction
 */
const fs = require('fs');

const searchString = '{const s=(0,a.makeResponse)(t.id,e);return"debug_traceTransaction"===t.method&&"object"==typeof e&&Array.isArray(e.structLogs)&&e.structLogs.length>this.BUFFERIFY_THRESHOLD?(0,u.bufferify)(s,""):JSON.stringify(s)}';

const replacementString = '{const r=(0,a.makeResponse)(t.id,e);if("debug_traceTransaction"===t.method&&"object"==typeof e&&Array.isArray(e.structLogs)&&e.structLogs.length>this.BUFFERIFY_THRESHOLD)return(0,u.bufferify)(r,"");try{return JSON.stringify(r)}catch(e){return(0,u.bufferify)(r,"")}}';

const filename = './node_modules/ganache/dist/node/1.js';
fs.readFile(filename, 'utf8', function (err,data) {
  if (err) {
    return console.log(err);
  }
  const result = data.replace(searchString, replacementString);

  fs.writeFile(filename, result, 'utf8', function (err) {
     if (err) return console.log(err);
  });
});

