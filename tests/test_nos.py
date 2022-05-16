from brownie import interface

def test_nos_gas(accounts):
    steth = interface.Lido('0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84')
    nos = interface.NodeOperatorsRegistry('0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5')
    
    operator = accounts.at('0x00000000219ab540356cbb839cbe05303d7705fa', force=True)
    oracle = accounts.at('0x442af784a788a5bd6f42a01ebe9f287a871243fb', force=True)
    depositor = accounts.at('0xDb149235B6F40dC08810AA69869783Be101790e7', force=True)
    voting= accounts.at('0x2e59A20f205bB85a89C53f1936454680651E618e', force=True)
    lido = accounts.at('0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84', force=True)

    nos.trimUnusedKeys({"from": lido})

    current_ops_count = nos.getActiveNodeOperatorsCount()
    tx = steth.pushBeacon(128084, 4160000, {"from": oracle})
    print(nos.getActiveNodeOperatorsCount(), tx.gas_used)
    operator.transfer(steth, 32 * 20*10**18)
    steth.depositBufferedEther({"from": depositor})     
    
    tx = steth.pushBeacon(128084, 4160500 * 10**18, {"from": oracle})
    print(nos.getActiveNodeOperatorsCount(), tx.gas_used)

    for i in range(100):
        for ops in range(10):
            nos.addNodeOperator(i, operator, {"from": voting})
            nos.addSigningKeysOperatorBH(current_ops_count+i*10+ops, 
                1, 
                '0x8e8013fb98d2b717e9b60e6b23546e00ec0ca11fb6b2336cd2e961d8115596665c6f20fec8f3efa67fb9b934ea4cf6cf', 
                '0x89526bd4b5d394899794251b02fa4b9eafdf72eebcdae2b7b09b38b66a27e568f33acb24793fbb636e1417a9b590802e0efb5992cd75a2cf14a6cb63e5739031925d6538580e8cd7af4e8d5cda820339dd773343bb40fb1f92ac1d4ed7d0928f',
                {"from": operator}) 
            nos.setNodeOperatorStakingLimit(current_ops_count+i*10+ops, 1, {"from": voting})

        operator.transfer(steth, 32 * 20*10**18)
        steth.depositBufferedEther({"from": depositor})     
        
        tx = steth.pushBeacon(128084, 4161000 * 10**18 + 10**19 * i, {"from": oracle})
        print(nos.getActiveNodeOperatorsCount(), tx.gas_used)
