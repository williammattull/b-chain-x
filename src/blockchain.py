import sys

import hashlib
import json

from time import time
from uuid import uuid4

from flask import Flask, jsonify, request

import requests
from urllib.parse import urlparse

class Blockchain(object):

    difficulty_target = "0000"

    def hash_block(selfself, block):
        block_encoded = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_encoded).hexdigest()

    def __init__(self):

        # store the address of other nodes on the blockchain
        self.nodes = set()

        # stores all the blocks in the entire blockchain
        self.chain = []

        # temporarily stores the transactions for the
        # current block
        self.current_transactions = []

        # create the genesis block with a specific fixed hash
        # of previous block genesis block starts with index 0
        genesis_hash = self.hash_block("genesis block")
        self.append_block(
            hash_of_previous_block=genesis_hash,
            nonce=self.proof_of_work(0, genesis_hash, [])
        )

    def add_node(self, address):
        """
        allow a new node to be added to the nodes member

        :param address:
        :return:
        """
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        """
        determine if a given blockchain is valid

        :param chain:
        :return:
        """

        # the genesis block
        last_block = chain[0]

        # starts with the second block
        current_index = 1

        while current_index < len(chain):

            block = chain[current_index]

            # check for valid hash recorded in the next block
            if block['hash_of_previous_block'] != self.hash_block(last_block):
                print("Failed hash compare check.")
                return False

            # check for valid nonce
            if not self.valid_proof(
                    current_index,
                    block['hash_of_previous_block'],
                    block['transactions'],
                    block['nonce']):
                print("Failed nonce proof check.")
                return False

            # move on to the next block on the chain
            last_block = block
            current_index += 1

        # the chain is valid
        return True

    def update_blockchain(self):
        """
        Check the blockchain from neighboring nodes is valid and the the node with
        the longest valid chain is the authoritative one; if another node with
        a valid blockchain is longer than the current one, it will replace the
        current blockchain.

        :return:
        """
        # get the neighboring nodes that have been registered
        neighbors = self.nodes
        new_chain = None

        # for simplicity, look for chains longer than ours
        max_length = len(self.chain)

        # collect and verify the chains from all the nodes in the blockchain network
        for node in neighbors:
            # collect the blockchain from the other nodes
            response = requests.get(f'http://{node}/blockchain')



            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # replace this node's chain if a new valid longer chain has been discovered
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def proof_of_work(self, index, hash_of_previous_block, transactions):
        """
        use PoW to find the nonce for the current block

        :param index:
        :param hash_of_previous_block:
        :param transactions:
        :return:
        """

        # try with nonce = 0
        nonce=0

        # try hashing the nonce together with the hash of the
        # previous block until it is valid
        while self.valid_proof(index, hash_of_previous_block, transactions, nonce) is False:
            nonce += 1

        return nonce

    def valid_proof(self, index, hash_of_previous_block, transactions, nonce):
        """
        hashes the content of a block and check to see if the block's hash meets the difficulty target

        :param index:
        :param hash_of_previous_block:
        :param transactions:
        :param nonce:
        :return:
        """

        # create string containing the hash of the previous
        # block and the block content, including the nonce
        content = f'{index}{hash_of_previous_block}{transactions}{nonce}'.encode()

        # hash using sha256
        content_hash = hashlib.sha256(content).hexdigest()

        # check if the hash meets the difficulty target
        return content_hash[:len(self.difficulty_target)] == self.difficulty_target

    def append_block(self, nonce, hash_of_previous_block):
        """
        creates a new block and adds it to the blockchain

        :param nonce:
        :param hash_of_previous_block:
        :return:
        """

        block = {
            'index': len(self.chain),
            'timestamp': time(),
            'transactions': self.current_transactions,
            'nonce': nonce,
            'hash_of_previous_block': hash_of_previous_block
        }

        # reset the current list of transactions
        self.current_transactions = []

        # add the new block to the blockchain
        self.chain.append(block)

        return block

    def add_transaction(self, sender, recipient, amount):
        """
        adds a new transaction to the current list of transactions

        :param sender:
        :param recipient:
        :param amount:
        :return:
        """
        self.current_transactions.append({
            'amount': amount,
            'recipient': recipient,
            'sender': sender
        })

        return self.last_block['index'] + 1

    @property
    def last_block(self):
        """
        returns the last block in the blockchain

        :return:
        """
        return self.chain[-1]


app = Flask(__name__)

# generate a globally unique address for this code
node_identifier = str(uuid4()).replace('-', "")

# instantiate the Blockchain
blockchain = Blockchain()

# return the entire blockchain
@app.route('/blockchain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }

    return jsonify(response), 200

# perform mining
@app.route('/mine', methods=['GET'])
def mine_block():
    blockchain.add_transaction(
        sender=0,
        recipient=node_identifier,
        amount=1,
    )

    # obtain the hash of last block in the blockchain
    last_block_hash = blockchain.hash_block(blockchain.last_block)

    # using PoW, get the nonce for the new block to be added
    # to the blockchain
    index = len(blockchain.chain)
    nonce = blockchain.proof_of_work(index, last_block_hash, blockchain.current_transactions)

    # add the new block to the blockchain using the last block
    # hash and the current nonce
    block = blockchain.append_block(nonce, last_block_hash)
    response = {
        'message': "New Block Mined",
        'index': block['index'],
        'hash_of_previous_block': block['hash_of_previous_block'],
        'nonce': block['nonce'],
        'transactions': block['transactions'],
    }

    return jsonify(response), 200

# add nodes to the chain
@app.route('/nodes/add_nodes', methods=['POST'])
def add_nodes():
    # get the nodes passed in from the client
    values = request.get_json()
    nodes = values.get('nodes')

    if nodes is None:
        return "Error: Missing node(s) info", 400

    for node in nodes:
        blockchain.add_node(node)

    response = {
        'message': 'New nodes added',
        'nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

# syncronize nodes
@app.route('/nodes/sync', methods=['GET'])
def sync():
    updated = blockchain.update_blockchain()
    if updated:
        response = {
            'message': 'The blockchain has ben updated to the latest',
            'blockchain': blockchain.chain
        }
    else:
        response = {
            'message': 'Current node blockchain is the latest',
            'blockchain': blockchain.chain
        }
    return jsonify(response), 200

# adding transactions
@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    # get the value passed in from the client
    values = request.get_json()

    # check that the required fields are in the POST'ed data
    required_fields = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required_fields):
        return ('Missing fields', 400)

    # create a new transaction
    index = blockchain.add_transaction(
        values['sender'],
        values['recipient'],
        values['amount']
    )

    response = {'message': f'Transaction will be added to Block {index}'}
    return (jsonify(response), 201)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(sys.argv[1]))