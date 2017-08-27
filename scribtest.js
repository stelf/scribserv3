
var socket = require('engine.io-client')('ws://localhost:9000');

socket.on('open', function(){
  socket.on('message', function(data){
      console.log(data);
  });
  socket.on('close', function(){
      console.log('stream closed');
  });
});
