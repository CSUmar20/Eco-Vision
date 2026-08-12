import { type Href, useRouter } from 'expo-router';
import { SymbolView } from 'expo-symbols';
import type { ComponentProps } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useLocationPreference } from '@/context/location-context';
import { useTheme } from '@/hooks/use-theme';

export default function SettingsScreen() {
  const router = useRouter();
  const theme = useTheme();
  const { jurisdiction } = useLocationPreference();

  return (
    <ScrollView style={{ backgroundColor: theme.background }} contentContainerStyle={styles.scroll}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <View style={styles.headingCopy}>
            <ThemedText type="smallBold" style={styles.eyebrow}>
              ECOVISION
            </ThemedText>
            <ThemedText type="title" style={styles.title}>
              Settings
            </ThemedText>
          </View>
          <Pressable
            accessibilityLabel="Close settings"
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

        <ThemedView type="backgroundElement" style={styles.section}>
          <ThemedText type="smallBold" style={styles.sectionLabel}>
            RECYCLING AREA
          </ThemedText>
          <View style={styles.settingRow}>
            <View style={styles.rowCopy}>
              <ThemedText type="smallBold">General location</ThemedText>
              <ThemedText type="small" themeColor="textSecondary">
                {jurisdiction ?? 'Not set'}
              </ThemedText>
            </View>
            <Pressable
              accessibilityRole="button"
              onPress={() => router.push('/location' as Href)}
              style={({ pressed }) => [styles.changeButton, pressed && styles.pressed]}>
              <ThemedText type="smallBold" style={styles.changeText}>
                {jurisdiction ? 'Change' : 'Set'}
              </ThemedText>
            </Pressable>
          </View>
        </ThemedView>

        <ThemedView type="backgroundElement" style={styles.section}>
          <ThemedText type="smallBold" style={styles.sectionLabel}>
            PRIVACY & DATA
          </ThemedText>
          <InfoRow
            detail="Photos are sent to the EcoVision API for classification and are not stored in PostgreSQL."
            icon={{ ios: 'photo.badge.checkmark', android: 'image', web: 'image' }}
            title="Photo handling"
          />
          <View style={[styles.divider, { backgroundColor: theme.backgroundSelected }]} />
          <InfoRow
            detail="No account is required. Scan corrections are saved anonymously to evaluate the model."
            icon={{ ios: 'person.crop.circle.badge.checkmark', android: 'person', web: 'person' }}
            title="Guest mode"
          />
          <View style={[styles.divider, { backgroundColor: theme.backgroundSelected }]} />
          <InfoRow
            detail="EcoVision follows your device's light or dark appearance setting."
            icon={{ ios: 'circle.lefthalf.filled', android: 'contrast', web: 'contrast' }}
            title="Appearance"
          />
        </ThemedView>

        <ThemedText type="small" themeColor="textSecondary" style={styles.footnote}>
          EcoVision identifies likely materials. It does not yet claim that an item is accepted by
          your local recycling program.
        </ThemedText>
      </SafeAreaView>
    </ScrollView>
  );
}

type InfoRowProps = {
  detail: string;
  icon: ComponentProps<typeof SymbolView>['name'];
  title: string;
};

function InfoRow({ detail, icon, title }: InfoRowProps) {
  return (
    <View style={styles.infoRow}>
      <View style={styles.infoIcon}>
        <SymbolView name={icon} size={22} tintColor="#52735b" />
      </View>
      <View style={styles.rowCopy}>
        <ThemedText type="smallBold">{title}</ThemedText>
        <ThemedText type="small" themeColor="textSecondary">
          {detail}
        </ThemedText>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { alignItems: 'center', paddingBottom: Spacing.five },
  safeArea: {
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
  section: { borderRadius: Spacing.four, padding: Spacing.three, gap: Spacing.three },
  sectionLabel: { color: '#52735b', fontSize: 11, letterSpacing: 1.4 },
  settingRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.three },
  infoRow: { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.three },
  infoIcon: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: '#dfe9da',
    alignItems: 'center',
    justifyContent: 'center',
  },
  rowCopy: { flex: 1, gap: Spacing.one },
  changeButton: {
    minHeight: 42,
    borderRadius: 21,
    backgroundColor: '#dfe9da',
    paddingHorizontal: Spacing.three,
    alignItems: 'center',
    justifyContent: 'center',
  },
  changeText: { color: '#345c43' },
  divider: { height: StyleSheet.hairlineWidth },
  footnote: { textAlign: 'center', paddingHorizontal: Spacing.three },
  pressed: { opacity: 0.72 },
});
