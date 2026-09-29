import { expect, mock, test } from 'bun:test';

// Render the composer as a React element tree while keeping native UI and picker APIs inert.
let stateIndex = 0;
mock.module('react', () => ({
  default: {},
  __CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE: { A: null, recentlyCreatedOwnerStacks: 0 },
  useState(initial: unknown) { return [stateIndex++ === 0 ? true : initial, () => {}]; },
  useRef(initial: unknown) { return { current: initial }; },
  useEffect() {},
}));
mock.module('react-native', () => {
  const View = 'View';
  return {
    View, Text: 'Text', TextInput: 'TextInput', TouchableOpacity: 'TouchableOpacity', Image: 'Image',
    StyleSheet: { create: (styles: unknown) => styles },
    Animated: {
      Value: class { interpolate() { return 0; } },
      spring: () => ({ start() {} }),
      View,
    },
    Keyboard: {}, Platform: { OS: 'android' }, LayoutAnimation: {}, UIManager: {}, Alert: {},
  };
});
mock.module('@expo/vector-icons', () => ({ Ionicons: 'Ionicons' }));
mock.module('expo-haptics', () => ({ ImpactFeedbackStyle: { Light: 'light', Medium: 'medium' }, impactAsync() {} }));
mock.module('expo-image-picker', () => ({}));
mock.module('expo-document-picker', () => ({}));
mock.module('../lib/fileTransfer', () => ({ readUriAsBase64() {} }));

const { CommandComposer } = await import('../components/CommandComposer');

function findSendToPC(element: any): any {
  if (!element || typeof element !== 'object') return null;
  if (element.props?.accessibilityLabel === 'Send files to PC') return element;
  const children = element.props?.children;
  for (const child of Array.isArray(children) ? children : [children]) {
    const found = findSendToPC(child);
    if (found) return found;
  }
  return null;
}

test('attachment menu opens the native PC file transfer panel', () => {
  stateIndex = 0;
  let opens = 0;
  let submits = 0;
  const tree = CommandComposer({
    queryText: '', setQueryText() {}, onSubmit() { submits++; }, onStop() {},
    status: 'idle', isConnected: true, isVoiceRecording: false,
    isVoiceTranscribing: false, onToggleVoice() {},
    onSendFilesToPC() { opens++; },
  });

  const action = findSendToPC(tree);
  expect(action).not.toBeNull();
  action.props.onPress();
  expect(opens).toBe(1);
  expect(submits).toBe(0);
});
