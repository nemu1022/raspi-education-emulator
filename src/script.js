// ============================================
// 実行ボタン
// ============================================

function runCode()
{
    const mainCode =
        document.getElementById("mainCode").value;

    const constCode =
        document.getElementById("constCode").value;

    console.log("RUN BUTTON");

    socket.send(JSON.stringify({
        type: "BUILD",
        main: mainCode,
        consts: constCode
    }));

    console.log("BUILD SENT");
}

// ============================================
// タブ切り替え
// ============================================

function showTab(name)
{
    const main =
        document.getElementById("mainCode");

    const constH =
        document.getElementById("constCode");

    if(name === "main")
    {
        main.style.display = "block";
        constH.style.display = "none";
    }
    else
    {
        main.style.display = "none";
        constH.style.display = "block";
    }
}

// ============================================
// WebSocket
// ============================================

const socket =
    new WebSocket(
        "ws://localhost:8765"
    );

// ============================================
// メッセージ受信
// ============================================

socket.onmessage = (event) =>
{
    console.log(
        "SERVER:",
        event.data
    );

    const led =
        document.getElementById("led");

    if(event.data === "LED_ON")
{
    console.log("LED ON RECEIVED");

    led.classList.remove("off");
    led.classList.add("on");
}

if(event.data === "LED_OFF")
{
    console.log("LED OFF RECEIVED");

    led.classList.remove("on");
    led.classList.add("off");
}


    if(event.data === "BUILD_OK")
    {
        alert("ビルド成功");
        return;
    }

    if(event.data === "BUILD_ERROR")
    {
        alert("ビルド失敗");
        return;
    }

    if(event.data === "QEMU_STARTED")
    {
        console.log("QEMU STARTED");
        return;
    }

    if(event.data.startsWith("QEMU_PID:"))
    {
        console.log(event.data);
        return;
    }
};