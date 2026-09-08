let sw1Pressed = false;
let programRunning = false;
let monitorId = null;

function runCode() {

    // ------------------
    // ソース取得
    // ------------------

    const mainCode =
        document.getElementById("mainCode").value;

    const constCode =
        document.getElementById("constCode").value;

    const fullSource =
        constCode +
        "\n" +
        mainCode;

    // ------------------
    // 画面部品取得
    // ------------------

    const led =
        document.getElementById("led");

    const log =
        document.getElementById("log");

    const registerView =
        document.getElementById("registers");

    const gpioView =
        document.getElementById("gpio");

    const messages = [];

    const timeline = [];
    let infiniteLoop = false;



    // ------------------
    // #define保存
    // ------------------

    const defines = {};

    // ------------------
    // レジスタ
    // ------------------

    const registers = {

        GPFSEL1: 0,
        GPSET0: 0,
        GPCLR0: 0,
        GPLEV0: 0

    };

    // ------------------
    // アドレス対応
    // ------------------

    const registerMap = {

        "0x3f200004": "GPFSEL1",
        "0x3f20001c": "GPSET0",
        "0x3f200028": "GPCLR0"

    };

    // ------------------
    // GPIO初期化
    // ------------------

    const gpio = {};

    for (let i = 0; i < 28; i++) {

        gpio[i] = {

            mode: "INPUT",
            value: 0

        };
    }

    messages.push(
        "SW1 = " +
        (sw1Pressed
            ? "PRESSED"
            : "RELEASED")
    );


    // ------------------
    // ソース解析
    // ------------------

    const lines =
        fullSource.split("\n");

    let executeCurrentBlock = true;

    for (let line of lines) {

        line = line.trim();

        if (
    line.startsWith("if") &&
    line.includes("SW1_PORT")
) {

    executeCurrentBlock =
        sw1Pressed;

    continue;
}

if (
    line.includes("else")
) {

    executeCurrentBlock =
        !sw1Pressed;

    continue;
}

        if (
            line.includes("*GPLEV0")
        ) {
            messages.push(
                "READ GPLEV0"
            );
        }

        if (
            line.includes("while(1)") ||
            line.includes("while (1)")
        ) {

            infiniteLoop = true;

            messages.push(
                "INFINITE LOOP DETECTED"
            );
        }

        // ------------------
        // #define解析
        // ------------------

        const forMatch =
            line.match(
                /for\s*\([^<]*<\s*([0-9,]+)/
            );

        if (forMatch) {

            const count =
                parseInt(
                    forMatch[1].replace(/,/g, "")
                );

            const ms =
                Math.round(
                    count / 690
                );

            timeline.push({
                type: "WAIT",
                ms: ms
            });

            messages.push(
                "WAIT " +
                ms +
                "ms"
            );
        }

        const defineMatch =
            line.match(/^#define\s+(\w+)\s+(\d+)/);

        if (defineMatch) {

            defines[
                defineMatch[1]
            ] =
                parseInt(
                    defineMatch[2]
                );

            messages.push(
                "DEFINE " +
                defineMatch[1] +
                " = " +
                defineMatch[2]
            );

            continue;
        }

        // ------------------
        // 生アドレス版
        // ------------------

        const addressMatch =
            line.match(/0x[0-9a-fA-F]+/);

        if (addressMatch) {

            const address =
                addressMatch[0];

            const register =
                registerMap[address];

            if (register) {

                messages.push(
                    "WRITE " +
                    address +
                    " -> " +
                    register
                );

                if (
                    register === "GPFSEL1"
                ) {

                    registers.GPFSEL1 = 1;
                }

                if (
                    register === "GPSET0"
                ) {

                    const shiftMatch =
                        line.match(
                            /1\s*<<\s*(\d+)/
                        );

                    if (shiftMatch) {

                        const pin =
                            parseInt(
                                shiftMatch[1]
                            );

                        registers.GPSET0 =
                            1 << pin;

                        timeline.push({
                            type: "LED",
                            state: "ON"
                        });
                    }
                }

                if (
                    register === "GPCLR0"
                ) {

                    const shiftMatch =
                        line.match(
                            /1\s*<<\s*(\d+)/
                        );

                    if (shiftMatch) {

                        const pin =
                            parseInt(
                                shiftMatch[1]
                            );

                        registers.GPCLR0 =
                            1 << pin;

                        timeline.push({
                            type: "LED",
                            state: "OFF"
                        });
                    }
                }
            }
        }

        // ------------------
        // *GPFSEL1
        // ------------------

        if (
            line.startsWith("*GPFSEL1")
        ) {
            const assignMatch =
                line.match(
                    /\*GPFSEL1\s*=\s*(\w+)/
                );

            if (assignMatch) {

                const target =
                    assignMatch[1];

                let value;

                if (
                    /^\d+$/.test(target)
                ) {
                    value =
                        parseInt(target);
                }
                else {
                    value =
                        defines[target];
                }

                if (
                    value !== undefined
                ) {

                    registers.GPFSEL1 =
                        value;

                    messages.push(
                        "WRITE GPFSEL1 = " +
                        value
                    );
                }
            }
        }

        // ------------------
        // *GPSET0
        // ------------------

        if (
    line.startsWith(
        "*GPSET0"
    )
) {

    if(!executeCurrentBlock){
        continue;
    }

    const shiftMatch =
        line.match(
            /1\s*<<\s*(\w+)/
        );

    if (shiftMatch) {

        const target =
            shiftMatch[1];

        let pin;

        if (
            /^\d+$/.test(target)
        ) {

            pin =
                parseInt(target);
        }
        else {

            pin =
                defines[target];
        }

        if (
            pin !== undefined
        ) {

            registers.GPSET0 =
                1 << pin;

            messages.push(
                "WRITE GPSET0 GPIO" +
                pin
            );

            timeline.push({
                type: "LED",
                state: "ON"
            });
        }
    }
}

        // ------------------
        // *GPCLR0
        // ------------------

        if (
    line.startsWith(
        "*GPCLR0"
    )
) {

    if (!executeCurrentBlock) {
        continue;
    }

    const shiftMatch =
        line.match(
            /1\s*<<\s*(\w+)/
        );

    if (shiftMatch) {

        const target =
            shiftMatch[1];

        let pin;

        if (
            /^\d+$/.test(target)
        ) {

            pin =
                parseInt(target);
        }
        else {

            pin =
                defines[target];
        }

        if (
            pin !== undefined
        ) {

            registers.GPCLR0 =
                1 << pin;

            messages.push(
                "WRITE GPCLR0 GPIO" +
                pin
            );

            timeline.push({
                type: "LED",
                state: "OFF"
            });
        }
    }
}
    }

    const sw1Port =
        defines["SW1_PORT"];

    if (
        sw1Pressed &&
        sw1Port !== undefined
    ) {

        registers.GPLEV0 =
            1 << sw1Port;

        messages.push(
            "SW1 PRESSED"
        );
    }
    else {

        registers.GPLEV0 = 0;

        messages.push(
            "SW1 RELEASED"
        );
    }


    // ------------------
    // GPFSEL1解析
    // GPIO10～19
    // ------------------

    for (let pin = 10; pin <= 19; pin++) {

        const shift =
            (pin - 10) * 3;

        const modeBits =
            (registers.GPFSEL1 >> shift) & 0b111;

        switch (modeBits) {

            case 0b001:

                gpio[pin].mode =
                    "OUTPUT";

                messages.push(
                    "GPIO" +
                    pin +
                    " MODE = OUTPUT"
                );

                break;

            case 0b000:

                gpio[pin].mode =
                    "INPUT";

                break;

            default:

                gpio[pin].mode =
                    "ALT";
        }
    }

    for (
        let pin = 0;
        pin < 28;
        pin++
    ) {
        if (
            registers.GPSET0 &
            (1 << pin)
        ) {

            gpio[pin].value = 1;

            messages.push(
                "GPIO" +
                pin +
                " = HIGH"
            );
        }

        if (
            registers.GPCLR0 &
            (1 << pin)
        ) {

            gpio[pin].value = 0;

            messages.push(
                "GPIO" +
                pin +
                " = LOW"
            );
        }
    }

    

    // ------------------
    // LED判定
    // ------------------

    // if (
    //     gpio[10].mode === "OUTPUT" &&
    //     gpio[10].value === 1
    // ) {

    //     led.classList.remove("off");
    //     led.classList.add("on");

    //     messages.push(
    //         "GREEN LED = ON"
    //     );
    // }
    // else {

    //     led.classList.remove("on");
    //     led.classList.add("off");

    //     messages.push(
    //         "GREEN LED = OFF"
    //     );
    // }

    // ------------------
    // レジスタ表示
    // ------------------

    registerView.textContent =
        `GPFSEL1 : 0x${registers.GPFSEL1.toString(16).padStart(8, "0")}
GPSET0  : 0x${registers.GPSET0.toString(16).padStart(8, "0")}
GPCLR0  : 0x${registers.GPCLR0.toString(16).padStart(8, "0")}
GPLEV0  : 0x${registers.GPLEV0.toString(16).padStart(8, "0")}`;

    // ------------------
    // GPIO表示
    // ------------------

    let gpioText = "";

    for (
        let i = 0;
        i < 28;
        i++
    ) {

        gpioText +=
            `GPIO${String(i).padStart(2, "0")}
Mode  : ${gpio[i].mode}
Value : ${gpio[i].value ? "HIGH" : "LOW"}

`;
    }

    gpioView.textContent =
        gpioText;

    // ------------------
    // ログ表示
    // ------------------

    log.textContent =
        messages.join("\n");

    console.log(timeline);


    replayTimeline(
        timeline,
        led,
        infiniteLoop
    );

    if (infiniteLoop) {

    startSwitchMonitor(
        defines,
        led
    );
}

}

    // ------------------
    // タブ切り替え
    // ------------------

    function showTab(name) {
        const main =
            document.getElementById("mainCode");

        const constH =
            document.getElementById("constCode");

        if (name === "main") {
            main.style.display =
                "block";

            constH.style.display =
                "none";
        }
        else {
            main.style.display =
                "none";

            constH.style.display =
                "block";
        }
    }

    async function replayTimeline(
        timeline,
        led,
        infiniteLoop
    ) {
        do {

            led.classList.remove("on");
            led.classList.add("off");

            for (const item of timeline) {

                if (item.type === "LED") {

                    if (item.state === "ON") {

                        led.classList.remove("off");
                        led.classList.add("on");
                    }
                    else {

                        led.classList.remove("on");
                        led.classList.add("off");
                    }

                    await new Promise(
                        resolve =>
                            setTimeout(
                                resolve,
                                300
                            )
                    );
                }

                if (item.type === "WAIT") {

                    await new Promise(
                        resolve =>
                            setTimeout(
                                resolve,
                                item.ms
                            )
                    );
                }
            }

        } while (infiniteLoop);
    }

function startSwitchMonitor(
    defines,
    led
) {

    if (monitorId) {

        clearInterval(
            monitorId
        );
    }

    programRunning = true;

    monitorId =
        setInterval(() => {

            if (sw1Pressed) {

                led.classList.remove(
                    "off"
                );

                led.classList.add(
                    "on"
                );
            }
            else {

                led.classList.remove(
                    "on"
                );

                led.classList.add(
                    "off"
                );
            }

        }, 50);
}

function stopProgram()
{
    programRunning = false;

    if (monitorId) {

        clearInterval(
            monitorId
        );

        monitorId = null;
    }
}

const socket = new WebSocket("ws://localhost:8765");

socket.onmessage = (event) => {

    const led =
        document.getElementById("led");

    if (event.data === "LED_ON") {

        led.classList.remove("off");
        led.classList.add("on");
    }

    if (event.data === "LED_OFF") {

        led.classList.remove("on");
        led.classList.add("off");
    }
};
