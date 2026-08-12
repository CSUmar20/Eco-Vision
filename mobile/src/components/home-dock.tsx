import { SymbolView } from 'expo-symbols';
import type { ComponentProps } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

type HomeDockProps = {
  disabled?: boolean;
  onAddPhoto: () => void;
  onHome: () => void;
  onSetLocation: () => void;
};

export function HomeDock({ disabled, onAddPhoto, onHome, onSetLocation }: HomeDockProps) {
  const insets = useSafeAreaInsets();
  const theme = useTheme();

  return (
    <ThemedView
      type="backgroundElement"
      style={[
        styles.dock,
        {
          borderColor: theme.backgroundSelected,
          paddingBottom: Math.max(insets.bottom, Spacing.two),
        },
      ]}>
      <DockButton
        disabled={disabled}
        label="Add photo"
        name={{ ios: 'photo.badge.plus', android: 'add_photo_alternate', web: 'add_photo_alternate' }}
        onPress={onAddPhoto}
      />

      <Pressable
        accessibilityLabel="Home"
        accessibilityRole="button"
        onPress={onHome}
        style={({ pressed }) => [styles.homeButton, pressed && styles.pressed]}>
        <SymbolView
          name={{ ios: 'house.fill', android: 'home', web: 'home' }}
          size={27}
          tintColor="#ffffff"
        />
        <ThemedText type="smallBold" style={styles.homeLabel}>
          Home
        </ThemedText>
      </Pressable>

      <DockButton
        disabled={disabled}
        label="Set location"
        name={{ ios: 'location.fill', android: 'location_on', web: 'location_on' }}
        onPress={onSetLocation}
      />
    </ThemedView>
  );
}

type DockButtonProps = {
  disabled?: boolean;
  label: string;
  name: ComponentProps<typeof SymbolView>['name'];
  onPress: () => void;
};

function DockButton({ disabled, label, name, onPress }: DockButtonProps) {
  const theme = useTheme();

  return (
    <Pressable
      accessibilityLabel={label}
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.dockButton,
        pressed && styles.pressed,
        disabled && styles.disabled,
      ]}>
      <View style={[styles.iconSurface, { backgroundColor: theme.background }]}>
        <SymbolView name={name} size={24} tintColor={theme.text} />
      </View>
      <ThemedText type="smallBold" style={styles.dockLabel}>
        {label}
      </ThemedText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  dock: {
    position: 'absolute',
    left: Spacing.three,
    right: Spacing.three,
    bottom: Spacing.two,
    minHeight: 84,
    borderRadius: 30,
    borderWidth: 1,
    paddingTop: Spacing.two,
    paddingHorizontal: Spacing.three,
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    shadowColor: '#183a2a',
    shadowOpacity: 0.14,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 10,
  },
  dockButton: {
    width: 92,
    minHeight: 62,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.one,
  },
  iconSurface: {
    width: 40,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dockLabel: {
    fontSize: 11,
    lineHeight: 14,
  },
  homeButton: {
    width: 76,
    height: 76,
    marginBottom: Spacing.two,
    borderRadius: 38,
    backgroundColor: '#78977a',
    borderWidth: 4,
    borderColor: '#f6f4ec',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 1,
    shadowColor: '#183a2a',
    shadowOpacity: 0.22,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 5 },
    elevation: 8,
  },
  homeLabel: {
    color: '#ffffff',
    fontSize: 10,
    lineHeight: 12,
  },
  pressed: {
    opacity: 0.7,
    transform: [{ scale: 0.97 }],
  },
  disabled: {
    opacity: 0.45,
  },
});
