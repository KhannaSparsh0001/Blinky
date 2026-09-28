# Implementation Plan: RevenueCat Paywall & Promo Code System for PC Controls

## 1. Objective
Restrict the "PC" section of the Blinky Expo mobile application (`common/mobile`) behind a monetization paywall.
- **Zero API keys or accounts required for end users**: The developer bundles their RevenueCat public key in the build. End users just open the app and tap "Subscribe" or "Redeem Code".
- **Direct Promo Code System**: Allow users to enter promotional / bypass codes (e.g. for Shipathon judges, testers, influencers, or direct APK downloads) to unlock PC controls immediately without payment.
- **BYOK for AI**: Users provide their own free Groq/DeepSeek API keys in PC settings (or use offline Ollama). Developer keys are never distributed.

---

## 2. Implementation Audit & Current Status

| File / Component | Purpose of Change | Status | Notes |
| :--- | :--- | :---: | :--- |
| [.env_example](file:///c:/Users/khann/Projects/Blinky/.env_example) | Environment variables for RevenueCat public key, entitlement ID, and promo codes. | ✅ **Implemented** | Added `EXPO_PUBLIC_REVENUECAT_GOOGLE_KEY`, `EXPO_PUBLIC_REVENUECAT_ENTITLEMENT_ID`, and `EXPO_PUBLIC_PROMO_CODES`. |
| [package.json](file:///c:/Users/khann/Projects/Blinky/common/mobile/package.json) | Add `react-native-purchases` and `react-native-purchases-ui`. | ⏳ **Pending** | Needs `react-native-purchases` and `react-native-purchases-ui` installed. |
| [app.json](file:///c:/Users/khann/Projects/Blinky/common/mobile/app.json) / `app.config.js` | Register the `react-native-purchases` Expo config plugin. | ⏳ **Pending** | Needs `react-native-purchases` added to plugins array. |
| `common/mobile/lib/purchases.ts` | RevenueCat service + Promo Code Engine: SDK init, entitlement verification (`hasPcAccess`), local promo code validation, and restore purchases handler. | ⏳ **Pending** | Not created yet. |
| `common/mobile/components/PromoCodeModal.tsx` | Dark-themed modal for entering voucher / promo codes. | ⏳ **Pending** | Not created yet. |
| [SystemScreen.tsx](file:///c:/Users/khann/Projects/Blinky/common/mobile/components/SystemScreen.tsx) | Display locked card with "Unlock PC Controls", "Enter Promo Code", and "Restore Purchases" when unentitled. | ⏳ **Pending** | Needs locked state UI and trigger handlers. |
| [App.tsx](file:///c:/Users/khann/Projects/Blinky/common/mobile/App.tsx) | Initialize RevenueCat on startup, intercept navigation to `'PC'` tab when locked, and present paywall or promo sheet. | ⏳ **Pending** | Needs initialization, entitlement state hook/subscription, and navigation intercept. |
| [BottomNavigation.tsx](file:///c:/Users/khann/Projects/Blinky/common/mobile/components/BottomNavigation.tsx) | Optional lock badge on the 'PC' icon when unentitled. | ⏳ **Pending** | Needs lock indicator when `!hasPcAccess`. |

---

## 3. Phased Implementation Roadmap

### Phase 0: Environment Specification ✅ (Completed)
- [x] Configure `.env_example` with public template variables:
  - `EXPO_PUBLIC_REVENUECAT_GOOGLE_KEY`
  - `EXPO_PUBLIC_REVENUECAT_ENTITLEMENT_ID`
  - `EXPO_PUBLIC_PROMO_CODES`

---

### Phase 1: Native Dependencies & Config Plugin ⏳ (Pending)
- [ ] Add `react-native-purchases` and `react-native-purchases-ui` to `common/mobile/package.json` (compatible with React Native 0.86 / Expo SDK 57).
- [ ] Register `react-native-purchases` in the `plugins` array of `common/mobile/app.json`.
- [ ] Add safe fallback environment configuration in `common/mobile` (or `.env`) so the app never crashes if keys are not yet configured.

---

### Phase 2: Core Monetization & Promo Engine Service ⏳ (Pending)
- [ ] Create `common/mobile/lib/purchases.ts`:
  - **Safe Initialization (`initializePurchases`)**: Safe startup check; guards against missing keys or Expo Go/unsupported native environments without throwing errors.
  - **Entitlement Checker (`hasPcAccess`)**: Unified entitlement query checking both:
    1. RevenueCat active entitlements for `pc_access` (or configured entitlement ID).
    2. Local redeemed promo codes persisted in `AsyncStorage`.
  - **Promo Code Validation (`redeemPromoCode(code)`)**:
    - Validates against configured promo codes (`EXPO_PUBLIC_PROMO_CODES`, e.g. `SHIPATHON`, `BLINKYVIP`, `EARLYBIRD`).
    - Persists unlock state in `AsyncStorage` (`@blinky_pc_promo_unlocked`).
    - Emits state change event or updates listeners for instant real-time reactive UI update.
  - **Paywall Presentation (`presentPcPaywall`)**:
    - Uses `RevenueCatUI.presentPaywallIfNeeded` or returns paywall status for custom handling.
  - **Purchase Restoration (`restorePurchases`)**:
    - Calls `Purchases.restorePurchases()` and synchronizes entitlement state.
  - **Listener / Subscription System**:
    - Subscribe to purchase/customer info updates to update React state across components.

---

### Phase 3: Promo & Paywall UI Components ⏳ (Pending)
- [ ] Create `common/mobile/components/PromoCodeModal.tsx`:
  - Sleek, dark-themed modal matching Blinky's cyber/glassmorphism design aesthetic (`colors.card`, `colors.border`, `colors.primary`).
  - Uppercase auto-capitalized input with clear button.
  - Haptic feedback on success/failure.
  - Instant unlock notification with success animations.
- [ ] Update `common/mobile/components/SystemScreen.tsx`:
  - When user lacks PC entitlement (`!hasPcAccess`):
    - Render a locked banner / paywall card replacing or overlaying sensitive PC controls (Wake-on-LAN, Power actions, System metrics).
    - Quick actions:
      - ⚡ **"Unlock PC Controls (Pro)"** -> Triggers RevenueCat paywall.
      - 🎟️ **"Redeem Promo Code"** -> Opens `PromoCodeModal`.
      - 🔄 **"Restore Purchases"** -> Triggers `restorePurchases()`.

---

### Phase 4: Navigation Interception & App Integration ⏳ (Pending)
- [ ] Update `common/mobile/App.tsx`:
  - Initialize RevenueCat on app start (`useEffect`).
  - Maintain reactive state for `isPcUnlocked`.
  - Intercept `'PC'` tab selection:
    - If user taps the `'PC'` tab and `!isPcUnlocked`, either:
      - Open the Paywall / Promo Code modal directly, OR
      - Navigate to `SystemScreen` where the lock card is prominently presented.
  - Re-evaluate lock status immediately upon successful promo redemption or purchase.
- [ ] Update `common/mobile/components/BottomNavigation.tsx`:
  - Add optional lock icon badge next to or on the `'PC'` tab icon when `!isPcUnlocked`.

---

### Phase 5: Verification & Quality Assurance ⏳ (Pending)
- [ ] Validate TypeScript build (`tsc --noEmit` or Metro type check) for `common/mobile`.
- [ ] Test promo code redemption flow:
  - Input `SHIPATHON` -> immediate unlock feedback & persistent storage.
  - Invalid code test -> clean error message without crash.
- [ ] Test persistence across restarts (verify `AsyncStorage` retrieval on app launch).
- [ ] Verify that non-PC tabs (Chat, Files, Actions) remain 100% accessible and unaffected.
