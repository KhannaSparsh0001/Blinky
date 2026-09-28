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
| [package.json](file:///c:/Users/khann/Projects/Blinky/common/mobile/package.json) | Add `react-native-purchases` and `react-native-purchases-ui`. | ✅ **Implemented** | Installed `react-native-purchases@^10.10.2` and `react-native-purchases-ui@^10.10.2`. |
| [app.json](file:///c:/Users/khann/Projects/Blinky/common/mobile/app.json) / `app.config.js` | Register the `react-native-purchases` Expo config plugin. | ✅ **Implemented** | Added `react-native-purchases` to `plugins` array. |
| [purchases.ts](file:///c:/Users/khann/Projects/Blinky/common/mobile/lib/purchases.ts) | RevenueCat service + Promo Code Engine: SDK init, entitlement verification (`hasPcAccess`), local promo code validation, and restore purchases handler. | ✅ **Implemented** | Implemented safe init, unified entitlement checks, promo code redemption, paywall presentation, and listener subscription. |
| [PromoCodeModal.tsx](file:///c:/Users/khann/Projects/Blinky/common/mobile/components/PromoCodeModal.tsx) | Dark-themed modal for entering voucher / promo codes. | ✅ **Implemented** | Created modal with drag-to-dismiss, uppercase input, clear button, haptics, and instant unlock feedback. |
| [SystemScreen.tsx](file:///c:/Users/khann/Projects/Blinky/common/mobile/components/SystemScreen.tsx) | Display locked card with "Unlock PC Controls", "Enter Promo Code", and "Restore Purchases" when unentitled. | ✅ **Implemented** | Added PRO status badges, paywall hero card with action buttons, and blurred locked controls wrapper. |
| [App.tsx](file:///c:/Users/khann/Projects/Blinky/common/mobile/App.tsx) | Initialize RevenueCat on startup, intercept navigation to `'PC'` tab when locked, and present paywall or promo sheet. | ✅ **Implemented** | Added SDK init, reactive `isPcUnlocked` listener, Paywall/Promo triggers, and `PromoCodeModal` rendering. |
| [BottomNavigation.tsx](file:///c:/Users/khann/Projects/Blinky/common/mobile/components/BottomNavigation.tsx) | Optional lock badge on the 'PC' icon when unentitled. | ✅ **Implemented** | Added `isPcLocked` prop and lock indicator badge over the PC tab icon. |

---

## 3. Phased Implementation Roadmap

### Phase 0: Environment Specification ✅ (Completed)
- [x] Configure `.env_example` with public template variables:
  - `EXPO_PUBLIC_REVENUECAT_GOOGLE_KEY`
  - `EXPO_PUBLIC_REVENUECAT_ENTITLEMENT_ID`
  - `EXPO_PUBLIC_PROMO_CODES`

---

### Phase 1: Native Dependencies & Config Plugin ✅ (Completed)
- [x] Add `react-native-purchases` and `react-native-purchases-ui` to `common/mobile/package.json` (compatible with React Native 0.86 / Expo SDK 57).
- [x] Register `react-native-purchases` in the `plugins` array of `common/mobile/app.json`.
- [x] Add safe fallback environment configuration in `common/mobile` (or `.env`) so the app never crashes if keys are not yet configured.
- [x] Verify TypeScript type safety (`bun x tsc --noEmit` passed with 0 errors).

---

### Phase 2: Core Monetization & Promo Engine Service ✅ (Completed)
- [x] Create `common/mobile/lib/purchases.ts`:
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
  - **Debug Helpers**: Added `resetPromoUnlockForDebug()` to easily toggle states during testing.
  - **Type Safety**: Verified zero TypeScript errors with `bun x tsc --noEmit`.

---

### Phase 3: Promo & Paywall UI Components ✅ (Completed)
- [x] Create `common/mobile/components/PromoCodeModal.tsx`:
  - Sleek, dark-themed modal matching Blinky's cyber/glassmorphism design aesthetic (`colors.card`, `colors.border`, `colors.primary`).
  - Uppercase auto-capitalized input with clear button and keyboard handling.
  - Haptic feedback on success/failure and drag-to-dismiss gesture handling.
  - Instant unlock notification with success states.
- [x] Update `common/mobile/components/SystemScreen.tsx`:
  - When user lacks PC entitlement (`!hasPcAccess` / `isLocked`):
    - Added `PRO LOCKED` / `PRO` status badge next to screen title.
    - Rendered high-converting paywall hero card with feature highlights.
    - Added quick-action buttons:
      - ⚡ **"Unlock PC Controls (Pro)"** -> Triggers `onUnlockPress`.
      - 🎟️ **"Redeem Promo Code"** -> Triggers `onPromoCodePress`.
      - 🔄 **"Restore Purchases"** -> Triggers `onRestorePress` with loading state.
    - Wrapped sensitive hardware metrics and power controls with semi-transparent disabled preview (`opacity: 0.35`, `pointerEvents: 'none'`).
  - Verified zero TypeScript compilation errors.

---

### Phase 4: Navigation Interception & App Integration ✅ (Completed)
- [x] Update `common/mobile/App.tsx`:
  - Initialize RevenueCat on app start (`useEffect`) with cleanup unmount.
  - Maintain reactive state for `isPcUnlocked` subscribed to `addPcAccessListener`.
  - Connect `SystemScreen` props (`isLocked`, `onUnlockPress`, `onPromoCodePress`, `onRestorePress`).
  - Wire `PromoCodeModal` bottom sheet modal for instant code validation and UI unlocking.
  - Handle paywall triggers with graceful fallback to promo modal on unsupported platforms.
- [x] Update `common/mobile/components/BottomNavigation.tsx`:
  - Added `isPcLocked` prop.
  - Rendered a lock indicator badge over the `'PC'` icon when locked.
  - Verified zero TypeScript compilation errors with `bun x tsc --noEmit`.

---

### Phase 5: Verification & Quality Assurance ✅ (Completed)
- [x] Validate TypeScript build (`bun x tsc --noEmit` passed with 0 errors).
- [x] Created automated test suite in `common/mobile/tests/purchases.test.ts`:
  - Verified default and configured promo code retrieval (`getAllowedPromoCodes`).
  - Tested promo code redemption flow with case/whitespace tolerance (`shipathon` -> instant unlock).
  - Tested invalid code rejection (empty string, non-matching code) with descriptive error messages.
  - Tested real-time subscriber notification (`addPcAccessListener`) upon unlock and reset.
  - Tested persistence in `AsyncStorage` (`@blinky_pc_promo_unlocked` survives and is readable on launch).
  - Tested purchase restore flow reporting existing promo unlocks.
  - Tested debug reset mechanism (`resetPromoUnlockForDebug`).
- [x] Ran automated test suite via Bun: **8 tests passed, 0 failures, 26 assertions verified**.
- [x] Verified non-PC tabs (Chat, Files, Actions) remain 100% accessible and completely unblocked.
