# =========================================
# HOL POS CLEAN MAKE SALES EDIT
# =========================================

# REMOVE RECENT LENS SALES SECTION
# Cleaner beginner-friendly optical POS


POS_CLEANER_HTML = """

<div class="step-box">

    <h3>Select Lens Category</h3>

    <div class="selection-grid">

        <button type="button"
                class="selection-btn selection-blue"
                onclick="loadLensType('SV')">

            👓 Single Vision

        </button>

        <button type="button"
                class="selection-btn selection-green"
                onclick="loadLensType('BIFOCAL')">

            📖 Bifocal

        </button>

        <button type="button"
                class="selection-btn selection-yellow"
                onclick="loadLensType('PROGRESSIVE')">

            ✨ Progressive

        </button>

    </div>

</div>


<div id="lensProductsArea">

    <!-- Lens products load here -->

</div>


<script>

function loadLensType(type){

    let area = document.getElementById("lensProductsArea");

    if(type === "SV"){

        area.innerHTML = `
        <div class="grid">

            <div class="product-card">
                <h4>SV White</h4>
                <button class="btn-green">
                    Select
                </button>
            </div>

            <div class="product-card">
                <h4>SV Photo AR</h4>
                <button class="btn-green">
                    Select
                </button>
            </div>

            <div class="product-card">
                <h4>SV Blue Cut Photo</h4>
                <button class="btn-green">
                    Select
                </button>
            </div>

        </div>
        `;
    }

    if(type === "BIFOCAL"){

        area.innerHTML = `
        <div class="grid">

            <div class="product-card">
                <h4>Bifocal White</h4>
                <button class="btn-green">
                    Select
                </button>
            </div>

            <div class="product-card">
                <h4>Bifocal Photo</h4>
                <button class="btn-green">
                    Select
                </button>
            </div>

        </div>
        `;
    }

    if(type === "PROGRESSIVE"){

        area.innerHTML = `
        <div class="grid">

            <div class="product-card">
                <h4>Progressive White</h4>
                <button class="btn-green">
                    Select
                </button>
            </div>

            <div class="product-card">
                <h4>Progressive Photo AR</h4>
                <button class="btn-green">
                    Select
                </button>
            </div>

        </div>
        `;
    }

}

</script>

"""

print("HOL POS Make Sales Cleaner Edit Loaded Successfully")
