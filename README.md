# wallet_app
仮想通貨とウォレットWebアプリの実装

## Progress
p2p組み込み完了

## how to start

## ブロックチェーンサーバ

最初のノードを立てる時は以下を実行(5000番にマイニングノードがたつ)

```$ python sample_server1.py```

二つ目以降のノードを立てるときは以下を実行(5000番以外を-pで指定)

```$ python sample_server2.py --c_host <c_host> --c_port <c_port> -p <port>```

|c_host|c_port|port|
|-|-|-|
|接続するノードのホスト(ip)|接続するノードのポート|サーバを立てるポート|
|defaultは自分のip|defaultは5000|defaultは5001|

<br>

## ウォレットサーバ

5000番に接続する時は以下を実行(50000番にウォレットノードがたつ)

```$ python wallet_app.py --c_host <c_host> --c_port <c_port> -p <port>```

|c_host|c_port|port|
|-|-|-|
|接続するノードのホスト(ip)|接続するノードのポート|サーバを立てるポート|
|defaultは自分のip|defaultは5000|defaultは50000|