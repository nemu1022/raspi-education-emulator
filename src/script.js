// ============================================
// 実行・停止ボタン
// ============================================

// 入力されたCプログラムをサーバーに送信して実行する
function runCode() {
    const mainCode = document.getElementById("mainCode").value;
    const constCode = document.getElementById("constCode").value;

    console.log("RUN BUTTON");

    socket.send(
        JSON.stringify({
            type: "BUILD",
            main: mainCode,
            consts: constCode
        })
    );

    console.log("BUILD SENT");
}

// 実行中のQEMU・GDBを停止する
function stopCode() {
    console.log("STOP BUTTON");

    socket.send(
        JSON.stringify({
            type: "STOP"
        })
    );
}

// ============================================
// main.c / const.h タブ切り替え
// ============================================

function showTab(name) {
    const main = document.getElementById("mainCode");
    const constH = document.getElementById("constCode");

    const mainTab = document.getElementById("mainTab");
    const constTab = document.getElementById("constTab");

    // main.c を表示
    if (name === "main") {
        main.style.display = "block";
        constH.style.display = "none";

        mainTab.classList.add("tab-selected");
        constTab.classList.remove("tab-selected");
    }

    // const.h を表示
    else {
        main.style.display = "none";
        constH.style.display = "block";

        mainTab.classList.remove("tab-selected");
        constTab.classList.add("tab-selected");
    }
}

// ============================================
// スイッチ状態
// ============================================

const switches = {
    sw1: false,
    sw2: false,
    sw3: false,
    sw4: false
};

// ============================================
// 8×8 ドットマトリックスLED
// ============================================

// 指定した行・列のLEDを点灯する
function matrixLedOn(row, col) {
    const led =
        document.getElementById(
            `matrix-${row}-${col}`
        );

    if (led) {
        led.classList.add("matrix-on");
    }
}

// 指定した行・列のLEDを消灯する
function matrixLedOff(row, col) {
    const led =
        document.getElementById(
            `matrix-${row}-${col}`
        );

    if (led) {
        led.classList.remove("matrix-on");
    }
}

// ============================================
// ページ読み込み時の初期化
// ============================================

window.addEventListener(
    "load",
    () => {
        // --------------------------------------------
        // main.c を初期表示
        // --------------------------------------------

        showTab("main");

        // --------------------------------------------
        // 8×8 ドットマトリックスLEDを生成
        // --------------------------------------------

        const matrix =
            document.getElementById("ledMatrix");

        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const dot =
                    document.createElement("div");

                dot.classList.add("matrix-led");

                dot.id =
                    `matrix-${row}-${col}`;

                matrix.appendChild(dot);
            }
        }

        // --------------------------------------------
        // SW1～SW4のイベントを登録
        // --------------------------------------------

        ["sw1", "sw2", "sw3", "sw4"]
            .forEach(id => {
                const button =
                    document.getElementById(id);

                // スイッチを押したとき
                button.onmousedown = () => {
                    switches[id] = true;

                    socket.send(
                        JSON.stringify({
                            type: "SWITCH",
                            switch: id,
                            value: 1
                        })
                    );
                };

                // スイッチを離したとき
                button.onmouseup = () => {
                    switches[id] = false;

                    socket.send(
                        JSON.stringify({
                            type: "SWITCH",
                            switch: id,
                            value: 0
                        })
                    );
                };

                // 押したままカーソルがボタン外へ移動したとき
                button.onmouseleave = () => {
                    switches[id] = false;

                    socket.send(
                        JSON.stringify({
                            type: "SWITCH",
                            switch: id,
                            value: 0
                        })
                    );
                };
            });
    }
);

// ============================================
// WebSocket接続
// ============================================

const socket =
    new WebSocket(
        "ws://localhost:8765"
    );


// WebSocket接続成功
socket.onopen = () => {
    console.log("WEBSOCKET CONNECTED");
};

// WebSocket切断
socket.onclose = () => {
    console.log("WEBSOCKET CLOSED");
};

// WebSocketエラー
socket.onerror = (error) => {
    console.error(
        "WEBSOCKET ERROR",
        error
    );
};

// ============================================
// ステータス表示
// ============================================

// ビルド結果や停止状態を画面内に表示する
function showStatus(message) {
    const status =
        document.getElementById("status");

    status.textContent = message;
}

// ============================================
// サーバーからのメッセージ受信
// ============================================

socket.onmessage = (event) => {
    console.log(
        "SERVER:",
        event.data
    );

    const led =
        document.getElementById("led");

    // --------------------------------------------
    // 通常LED 点灯
    // --------------------------------------------

    if (event.data === "LED_ON") {
        led.classList.remove("off");
        led.classList.add("on");

        console.log(
            "LED ON:",
            Date.now()
        );

        return;
    }

    // --------------------------------------------
    // 通常LED 消灯
    // --------------------------------------------

    if (event.data === "LED_OFF") {
        led.classList.remove("on");
        led.classList.add("off");

        console.log(
            "LED OFF:",
            Date.now()
        );

        return;
    }

    // --------------------------------------------
    // ビルド成功
    // --------------------------------------------

    if (event.data === "BUILD_OK") {
        showStatus("ビルド成功");
        return;
    }

    // --------------------------------------------
    // ビルド失敗
    // --------------------------------------------

    if (event.data === "BUILD_ERROR") {
        showStatus("ビルド失敗");
        return;
    }

    // --------------------------------------------
    // QEMU起動完了
    // --------------------------------------------

    if (event.data === "QEMU_STARTED") {
        console.log("QEMU STARTED");
        return;
    }

    // --------------------------------------------
    // QEMUプロセスID
    // --------------------------------------------

    if (event.data.startsWith("QEMU_PID:")) {
        console.log(event.data);
        return;
    }

    // --------------------------------------------
    // 実行停止
    // --------------------------------------------

    if (event.data === "STOPPED") {
        console.log("QEMU STOPPED");

        // 通常LEDを消灯状態へ戻す
        led.classList.remove("on");
        led.classList.add("off");

        showStatus("停止しました");

        return;
    }
};