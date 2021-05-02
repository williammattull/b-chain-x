# b-chain-x
This is my toy blockchain inspired by the book *Beginnning Ethereum Smart Contracts Programming* by Wei-Meng Lee.

To start the blockchain server, open a terminal window:  
`python blockchain.py 5000`

Start another terminal, view the blockchain:  
`curl http://localhost:5000/blockchain`  
  
Mine queued transactions:  
`curl http://localhost:5000/mine`  
  
POST transaction:
`curl -X POST -H "Content-Type: application/json" -d '{"sender": "04d0988bfa799f7d7ef9ab3de97ef481", "recipient": "cd0f75d2367ad456607647edde665d6f", "amount": 5}' "http://localhost:5000/transactions/new"`  



