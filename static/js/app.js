/**
 * B-Side Records POS - Frontend Application Logic
 */

// Application State
let products = [];
let cart = [];

// DOM Elements
const productsContainer = document.getElementById('products-container');
const loadingSpinner = document.getElementById('loading-spinner');
const emptyCatalogMessage = document.getElementById('empty-catalog-message');
const searchInput = document.getElementById('search-input');
const filterArtist = document.getElementById('filter-artist');
const refreshBtn = document.getElementById('btn-refresh');


const emptyCartMessage = document.getElementById('empty-cart-message');
const cartItemsList = document.getElementById('cart-items-list');
const cartTotal = document.getElementById('cart-total');
const checkoutBtn = document.getElementById('btn-checkout');
const clearCartBtn = document.getElementById('btn-clear-cart');
const alertContainer = document.getElementById('alert-container');

/**
 * Show a notification message (toast) to the user.
 * @param {string} message - Message to display
 * @param {'success'|'danger'} type - Notification type
 */
function showAlert(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `custom-toast custom-toast-${type}`;
    
    const icon = type === 'success' ? 'bi-check-circle-fill' : 'bi-exclamation-triangle-fill';
    
    toast.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="bi ${icon} me-2 fs-5"></i>
            <span>${message}</span>
        </div>
        <button type="button" class="btn-close btn-close-white ms-3" aria-label="Close"></button>
    `;
    
    // Setup close button listener
    const closeBtn = toast.querySelector('.btn-close');
    closeBtn.addEventListener('click', () => {
        toast.remove();
    });
    
    alertContainer.appendChild(toast);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 4000);
}

/**
 * Fetch available stock / inventory from API (UC-2)
 */
async function fetchProducts() {
    loadingSpinner.classList.remove('d-none');
    productsContainer.classList.add('d-none');
    emptyCatalogMessage.classList.add('d-none');
    
    try {
        const response = await fetch('/api/products');
        if (!response.ok) {
            throw new Error('Error de servidor al cargar productos.');
        }
        
        products = await response.json();
        
        populateArtistFilter();
        renderProducts();
    } catch (error) {
        console.error('Error loading products:', error);
        showAlert('No se pudo cargar el inventario de productos.', 'danger');
        loadingSpinner.classList.add('d-none');
    }
}

/**
 * Populates the artist filter select element.
 */
function populateArtistFilter() {
    const currentSelection = filterArtist.value;
    
    // Extract unique artist names
    const artists = [...new Set(products.map(p => p.artist_name))].sort();
    
    // Reset options
    filterArtist.innerHTML = '<option value="">Todos los artistas</option>';
    
    artists.forEach(artist => {
        const option = document.createElement('option');
        option.value = artist;
        option.textContent = artist;
        filterArtist.appendChild(option);
    });
    
    // Restore selection if it still exists
    if (artists.includes(currentSelection)) {
        filterArtist.value = currentSelection;
    }
}

/**
 * Render catalog products with filters applied (UC-2)
 */
function renderProducts() {
    const query = searchInput.value.toLowerCase().trim();
    const artistFilter = filterArtist.value;
    
    // Filter products list
    const filtered = products.filter(product => {
        const matchesSearch = 
            product.name.toLowerCase().includes(query) ||
            product.artist_name.toLowerCase().includes(query) ||
            product.genre.toLowerCase().includes(query);
            
        const matchesArtist = !artistFilter || product.artist_name === artistFilter;
        
        return matchesSearch && matchesArtist;
    });
    
    // Toggle loading views
    loadingSpinner.classList.add('d-none');
    
    if (filtered.length === 0) {
        productsContainer.classList.add('d-none');
        emptyCatalogMessage.classList.remove('d-none');
        return;
    }
    
    emptyCatalogMessage.classList.add('d-none');
    productsContainer.classList.remove('d-none');
    
    productsContainer.innerHTML = '';
    
    filtered.forEach(product => {
        const isOutOfStock = product.stock <= 0;
        let stockBadgeClass = 'badge-stock-in';
        let stockText = `${product.stock} unidades`;
        
        if (isOutOfStock) {
            stockBadgeClass = 'badge-stock-out';
            stockText = 'Agotado';
        } else if (product.stock <= 5) {
            stockBadgeClass = 'badge-stock-low';
            stockText = `Bajo stock: ${product.stock} un.`;
        }
        
        const cardCol = document.createElement('div');
        cardCol.className = 'col';
        cardCol.innerHTML = `
            <div class="product-card h-100 d-flex flex-column justify-content-between ${isOutOfStock ? 'opacity-75' : ''}" 
                 data-id="${product.id}">
                <div>
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <span class="artist-badge">${product.artist_name}</span>
                        <span class="badge badge-stock ${stockBadgeClass}">${stockText}</span>
                    </div>
                    <h3 class="product-title text-white mt-1">${product.name}</h3>
                    <p class="text-muted small mb-3"><i class="bi bi-tag-fill me-1"></i>${product.genre}</p>
                </div>
                <div class="d-flex justify-content-between align-items-center mt-auto pt-2">
                    <span class="product-price">$${product.price.toFixed(2)}</span>
                    <button class="btn btn-outline-light btn-sm add-to-cart-btn" 
                            ${isOutOfStock ? 'disabled' : ''}>
                        <i class="bi bi-plus-lg me-1"></i>Agregar
                    </button>
                </div>
            </div>
        `;
        
        // Add click listener to card (add to cart)
        const card = cardCol.querySelector('.product-card');
        const addBtn = cardCol.querySelector('.add-to-cart-btn');
        
        const actionAdd = (e) => {
            e.stopPropagation();
            if (!isOutOfStock) {
                addToCart(product.id);
            }
        };
        
        card.addEventListener('click', actionAdd);
        addBtn.addEventListener('click', actionAdd);
        
        productsContainer.appendChild(cardCol);
    });
}

/**
 * Add product to cart (UC-1)
 * @param {number} productId 
 */
function addToCart(productId) {
    const product = products.find(p => p.id === productId);
    if (!product || product.stock <= 0) return;
    
    const cartItem = cart.find(item => item.product_id === productId);
    
    if (cartItem) {
        if (cartItem.quantity + 1 > product.stock) {
            showAlert(`No puedes agregar más de este producto. Stock disponible: ${product.stock}`, 'danger');
            return;
        }
        cartItem.quantity += 1;
    } else {
        cart.push({
            product_id: productId,
            name: product.name,
            price: product.price,
            stock: product.stock,
            quantity: 1
        });
    }
    
    renderCart();
    showAlert(`'${product.name}' agregado al carrito.`);
}

/**
 * Update quantity of a product in the cart (UC-1)
 * @param {number} productId 
 * @param {number} delta - change in quantity (+1 or -1)
 */
function updateCartQuantity(productId, delta) {
    const item = cart.find(i => i.product_id === productId);
    if (!item) return;
    
    const newQty = item.quantity + delta;
    
    if (newQty <= 0) {
        removeFromCart(productId);
        return;
    }
    
    if (newQty > item.stock) {
        showAlert(`Cantidad supera el stock disponible de ${item.stock} unidades.`, 'danger');
        return;
    }
    
    item.quantity = newQty;
    renderCart();
}

/**
 * Remove item from cart (UC-1)
 * @param {number} productId 
 */
function removeFromCart(productId) {
    const itemIndex = cart.findIndex(i => i.product_id === productId);
    if (itemIndex === -1) return;
    
    const itemName = cart[itemIndex].name;
    cart.splice(itemIndex, 1);
    
    renderCart();
    showAlert(`'${itemName}' eliminado del carrito.`, 'danger');
}

/**
 * Empty all items from the cart.
 */
function clearCart() {
    if (cart.length === 0) return;
    cart = [];
    renderCart();
    showAlert('Carrito vaciado.', 'danger');
}

/**
 * Render cart items and calculate totals (UC-1)
 */
function renderCart() {
    if (cart.length === 0) {
        emptyCartMessage.classList.remove('d-none');
        cartItemsList.classList.add('d-none');
        checkoutBtn.disabled = true;
        cartTotal.textContent = '$0.00';
        return;
    }
    
    emptyCartMessage.classList.add('d-none');
    cartItemsList.classList.remove('d-none');
    checkoutBtn.disabled = false;
    
    cartItemsList.innerHTML = '';
    let total = 0;
    
    cart.forEach(item => {
        const subtotal = item.price * item.quantity;
        total += subtotal;
        
        const itemRow = document.createElement('div');
        itemRow.className = 'cart-item d-flex align-items-center justify-content-between';
        itemRow.innerHTML = `
            <div class="flex-grow-1 me-2">
                <div class="fw-bold text-white small text-truncate" style="max-width: 180px;">${item.name}</div>
                <div class="text-neon-blue small">$${item.price.toFixed(2)} c/u</div>
            </div>
            <div class="d-flex align-items-center me-3">
                <button class="qty-btn btn-dec"><i class="bi bi-dash"></i></button>
                <span class="qty-val text-white px-2">${item.quantity}</span>
                <button class="qty-btn btn-inc"><i class="bi bi-plus"></i></button>
            </div>
            <div class="text-end me-3">
                <span class="fw-bold text-white small">$${subtotal.toFixed(2)}</span>
            </div>
            <div>
                <i class="bi bi-x-circle-fill cart-item-remove"></i>
            </div>
        `;
        
        // Hook events
        itemRow.querySelector('.btn-dec').addEventListener('click', () => updateCartQuantity(item.product_id, -1));
        itemRow.querySelector('.btn-inc').addEventListener('click', () => updateCartQuantity(item.product_id, 1));
        itemRow.querySelector('.cart-item-remove').addEventListener('click', () => removeFromCart(item.product_id));
        
        cartItemsList.appendChild(itemRow);
    });
    
    cartTotal.textContent = `$${total.toFixed(2)}`;
}

/**
 * Post sale details to backend database (UC-1)
 */
async function checkout() {
    if (cart.length === 0) return;
    
    // Disable elements while submitting
    checkoutBtn.disabled = true;
    const originalBtnHTML = checkoutBtn.innerHTML;
    checkoutBtn.innerHTML = `
        <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
        Procesando...
    `;
    
    // Format cart payload
    const payload = {
        items: cart.map(item => ({
            product_id: item.product_id,
            quantity: item.quantity
        }))
    };
    
    try {
        const response = await fetch('/api/sales', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Error al procesar la venta.');
        }
        
        showAlert('¡Venta realizada exitosamente!', 'success');
        cart = [];
        renderCart();
        
        // Refresh products list to show updated stock levels
        await fetchProducts();
    } catch (error) {
        console.error('Checkout error:', error);
        showAlert(error.message, 'danger');
    } finally {
        checkoutBtn.innerHTML = originalBtnHTML;
        checkoutBtn.disabled = cart.length === 0;
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', fetchProducts);
searchInput.addEventListener('input', renderProducts);
filterArtist.addEventListener('change', renderProducts);
refreshBtn.addEventListener('click', fetchProducts);
clearCartBtn.addEventListener('click', clearCart);
checkoutBtn.addEventListener('click', checkout);
