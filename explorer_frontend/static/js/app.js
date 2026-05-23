async function loadStats() {

    const res =
        await fetch("/api/stats");

    const data =
        await res.json();

    if (data.error) {

        console.log(data.error);
        return;
    }

    document.getElementById(
        "height"
    ).innerText = data.height;

    document.getElementById(
        "difficulty"
    ).innerText = data.difficulty;

    document.getElementById(
        "hashrate"
    ).innerText = data.hashrate;

    document.getElementById(
        "supply"
    ).innerText = data.supply;

    document.getElementById(
        "peers"
    ).innerText = data.peers;

    document.getElementById(
        "pending"
    ).innerText = data.pending_txs;

    document.getElementById(
        "latest"
    ).innerHTML = `

        <b>Height:</b>
        ${data.latest_block.index}
        <br><br>

        <b>Hash:</b>
        ${data.latest_hash}
        <br><br>

        <b>Nonce:</b>
        ${data.latest_block.nonce}
        <br><br>

        <b>Timestamp:</b>
        ${data.latest_block.timestamp}

    `;
}

async function loadBlocks() {

    const res =
        await fetch("/api/blocks");

    const blocks =
        await res.json();

    const tbody =
        document.getElementById(
            "blocks"
        );

    tbody.innerHTML = "";

    blocks.forEach(block => {

        const row =
            document.createElement("tr");

        row.innerHTML = `

            <td>${block.index}</td>

            <td>
            ${block.hash.substring(0,24)}...
            </td>

            <td>
            ${block.difficulty || 1}
            </td>

            <td>
            ${block.transactions.length}
            </td>

            <td>
            ${new Date(
                block.timestamp * 1000
            ).toLocaleString()}
            </td>
        `;

        tbody.appendChild(row);
    });
}

async function refresh() {

    await loadStats();
    await loadBlocks();
}

refresh();

setInterval(
    refresh,
    5000
);
