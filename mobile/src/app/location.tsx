import { useRouter } from 'expo-router';
import { SymbolView } from 'expo-symbols';
import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useLocationPreference } from '@/context/location-context';
import { useTheme } from '@/hooks/use-theme';

export default function LocationScreen() {
  const router = useRouter();
  const theme = useTheme();
  const { jurisdiction, setJurisdiction } = useLocationPreference();
  const [locationInput, setLocationInput] = useState(jurisdiction ?? '');
  const normalizedLocation = locationInput.trim();
  const canSave = normalizedLocation.length >= 3;

  function saveLocation() {
    if (!canSave) {
      return;
    }

    setJurisdiction(normalizedLocation);
    router.back();
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={[styles.screen, { backgroundColor: theme.background }]}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.content}>
          <View style={styles.header}>
            <View style={styles.headingCopy}>
              <ThemedText type="smallBold" style={styles.eyebrow}>
                GENERAL AREA
              </ThemedText>
              <ThemedText type="title" style={styles.title}>
                Set your location
              </ThemedText>
            </View>
            <Pressable
              accessibilityLabel="Close location settings"
              accessibilityRole="button"
              onPress={() => router.back()}
              style={({ pressed }) => [
                styles.closeButton,
                { backgroundColor: theme.backgroundElement },
                pressed && styles.pressed,
              ]}>
              <SymbolView
                name={{ ios: 'xmark', android: 'close', web: 'close' }}
                size={22}
                tintColor={theme.text}
              />
            </Pressable>
          </View>

          <ThemedText themeColor="textSecondary" style={styles.description}>
            Enter a ZIP or postal code, or a city and state/province. EcoVision does not need your
            street address or a live GPS trail.
          </ThemedText>

          <View style={styles.form}>
            <ThemedText type="smallBold">ZIP, postal code, or city</ThemedText>
            <TextInput
              accessibilityLabel="ZIP, postal code, or city"
              autoCapitalize="words"
              autoCorrect={false}
              onChangeText={setLocationInput}
              onSubmitEditing={saveLocation}
              placeholder="Example: Austin, TX or 78701"
              placeholderTextColor={theme.textSecondary}
              returnKeyType="done"
              style={[
                styles.input,
                {
                  borderColor: theme.backgroundSelected,
                  backgroundColor: theme.backgroundElement,
                  color: theme.text,
                },
              ]}
              value={locationInput}
            />
            <ThemedText type="small" themeColor="textSecondary">
              This beta keeps the selection only while the app is open. Local disposal rules are
              not connected yet.
            </ThemedText>
          </View>

          <ThemedView type="backgroundElement" style={styles.privacyCard}>
            <View style={styles.privacyIcon}>
              <SymbolView
                name={{ ios: 'location.slash.fill', android: 'location_off', web: 'location_off' }}
                size={24}
                tintColor="#52735b"
              />
            </View>
            <View style={styles.privacyCopy}>
              <ThemedText type="smallBold">Privacy by design</ThemedText>
              <ThemedText type="small" themeColor="textSecondary">
                A general recycling jurisdiction is enough to match official local guidance later.
              </ThemedText>
            </View>
          </ThemedView>

          <Pressable
            accessibilityRole="button"
            disabled={!canSave}
            onPress={saveLocation}
            style={({ pressed }) => [
              styles.saveButton,
              pressed && styles.pressed,
              !canSave && styles.disabled,
            ]}>
            <ThemedText type="smallBold" style={styles.saveButtonText}>
              Save general area
            </ThemedText>
          </Pressable>
        </View>
      </SafeAreaView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  safeArea: { flex: 1, alignItems: 'center' },
  content: {
    width: '100%',
    maxWidth: MaxContentWidth,
    padding: Spacing.four,
    gap: Spacing.four,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: Spacing.three,
  },
  headingCopy: { flex: 1, gap: Spacing.two },
  eyebrow: { color: '#52735b', letterSpacing: 1.6 },
  title: { fontSize: 40, lineHeight: 46 },
  closeButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  description: { maxWidth: 600 },
  form: { gap: Spacing.two },
  input: {
    minHeight: 58,
    borderRadius: Spacing.three,
    borderWidth: 1,
    paddingHorizontal: Spacing.three,
    fontSize: 17,
  },
  privacyCard: {
    borderRadius: Spacing.three,
    padding: Spacing.three,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
  },
  privacyIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#dfe9da',
    alignItems: 'center',
    justifyContent: 'center',
  },
  privacyCopy: { flex: 1, gap: Spacing.one },
  saveButton: {
    minHeight: 54,
    borderRadius: Spacing.three,
    backgroundColor: '#78977a',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: Spacing.four,
  },
  saveButtonText: { color: '#ffffff' },
  pressed: { opacity: 0.72 },
  disabled: { opacity: 0.42 },
});
