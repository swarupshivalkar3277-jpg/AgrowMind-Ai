import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { addCartItem, getCart, removeCartItem, updateCartItem } from "../services/authService";
import { useAuth } from "./AuthContext";

const CartContext = createContext(null);

const emptyCart = { items: [], subtotal: 0, tax: 0, shipping: 0, total: 0, count: 0 };

export function CartProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [cart, setCart] = useState(emptyCart);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  async function refreshCart() {
    if (!isAuthenticated) {
      setCart(emptyCart);
      return emptyCart;
    }

    const { data } = await getCart();
    setCart(data.cart || emptyCart);
    return data.cart || emptyCart;
  }

  useEffect(() => {
    refreshCart().catch(() => setCart(emptyCart));
  }, [isAuthenticated]);

  async function add(productId, quantity = 1) {
    setLoading(true);
    try {
      const { data } = await addCartItem(productId, quantity);
      setCart(data.cart || emptyCart);
      setDrawerOpen(true);
    } finally {
      setLoading(false);
    }
  }

  async function update(productId, quantity) {
    setLoading(true);
    try {
      const { data } = quantity <= 0
        ? await removeCartItem(productId)
        : await updateCartItem(productId, quantity);
      setCart(data.cart || emptyCart);
    } finally {
      setLoading(false);
    }
  }

  async function remove(productId) {
    setLoading(true);
    try {
      const { data } = await removeCartItem(productId);
      setCart(data.cart || emptyCart);
    } finally {
      setLoading(false);
    }
  }

  const value = useMemo(
    () => ({
      add,
      cart,
      drawerOpen,
      loading,
      refreshCart,
      remove,
      setDrawerOpen,
      update,
    }),
    [cart, drawerOpen, loading]
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error("useCart must be used inside CartProvider");
  }
  return context;
}
