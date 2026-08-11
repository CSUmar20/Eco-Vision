import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { classifyImage, type ScanResult } from '@/api/classify';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

function formatConfidence(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export default function HomeScreen() {
  const theme = useTheme();
  const [selectedImage, setSelectedImage] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  function usePickedImage(result: ImagePicker.ImagePickerResult) {
    if (!result.canceled && result.assets[0]) {
      setSelectedImage(result.assets[0]);
      setScanResult(null);
      setErrorMessage(null);
    }
  }

  async function chooseImage() {
    setErrorMessage(null);

    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsEditing: false,
        quality: 0.9,
      });

      usePickedImage(result);
    } catch {
      setErrorMessage('The photo library could not be opened. Please try again.');
    }
  }

  async function takePhoto() {
    setErrorMessage(null);

    try {
      if (Platform.OS !== 'web') {
        const permission = await ImagePicker.requestCameraPermissionsAsync();

        if (!permission.granted) {
          setErrorMessage('Camera access is required to photograph an item.');
          return;
        }
      }

      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ['images'],
        cameraType: ImagePicker.CameraType.back,
        allowsEditing: false,
        quality: 0.9,
      });

      usePickedImage(result);
    } catch {
      setErrorMessage('The camera could not be opened. Please try again.');
    }
  }

  async function scanImage() {
    if (!selectedImage || isLoading) {
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setScanResult(null);

    try {
      const result = await classifyImage(selectedImage);
      setScanResult(result);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'The image could not be scanned.');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <ScrollView
      style={[styles.scrollView, { backgroundColor: theme.background }]}
      contentContainerStyle={styles.scrollContent}>
      <SafeAreaView style={styles.safeArea} edges={['top', 'left', 'right']}>
        <View style={styles.header}>
          <View style={styles.eyebrowRow}>
            <View style={styles.logoMark} />
            <ThemedText type="smallBold" style={styles.eyebrow}>
              ECOVISION
            </ThemedText>
          </View>
          <ThemedText type="title" style={styles.title}>
            Scan an item.
          </ThemedText>
          <ThemedText style={styles.subtitle} themeColor="textSecondary">
            Choose one clear photo and EcoVision will identify the item and show its closest
            matches.
          </ThemedText>
        </View>

        <ThemedView type="backgroundElement" style={styles.scanCard}>
          {selectedImage ? (
            <Image source={{ uri: selectedImage.uri }} style={styles.preview} contentFit="cover" />
          ) : (
            <View style={[styles.emptyPreview, { borderColor: theme.textSecondary }]}>
              <ThemedText style={styles.emptyIcon}>♻</ThemedText>
              <ThemedText type="smallBold">No photo selected</ThemedText>
              <ThemedText type="small" themeColor="textSecondary" style={styles.centerText}>
                Place one item in the center of the frame for the clearest result.
              </ThemedText>
            </View>
          )}

          <View style={styles.actions}>
            <Pressable
              accessibilityRole="button"
              disabled={isLoading}
              onPress={chooseImage}
              style={({ pressed }) => [
                styles.secondaryButton,
                { borderColor: theme.text },
                pressed && styles.pressed,
              ]}>
              <ThemedText type="smallBold">
                {selectedImage ? 'Choose another photo' : 'Choose from library'}
              </ThemedText>
            </Pressable>

            <Pressable
              accessibilityRole="button"
              disabled={isLoading}
              onPress={takePhoto}
              style={({ pressed }) => [
                styles.secondaryButton,
                { borderColor: theme.text },
                pressed && styles.pressed,
              ]}>
              <ThemedText type="smallBold">Take a photo</ThemedText>
            </Pressable>

            {selectedImage && (
              <Pressable
                accessibilityRole="button"
                disabled={isLoading}
                onPress={scanImage}
                style={({ pressed }) => [
                  styles.primaryButton,
                  pressed && styles.pressed,
                  isLoading && styles.disabled,
                ]}>
                {isLoading ? (
                  <>
                    <ActivityIndicator color="#ffffff" />
                    <ThemedText type="smallBold" style={styles.primaryButtonText}>
                      Analyzing…
                    </ThemedText>
                  </>
                ) : (
                  <ThemedText type="smallBold" style={styles.primaryButtonText}>
                    Analyze item
                  </ThemedText>
                )}
              </Pressable>
            )}
          </View>
        </ThemedView>

        {errorMessage && (
          <View accessibilityRole="alert" style={styles.errorCard}>
            <ThemedText type="smallBold" style={styles.errorTitle}>
              Scan unsuccessful
            </ThemedText>
            <ThemedText type="small" style={styles.errorText}>
              {errorMessage}
            </ThemedText>
            {selectedImage && (
              <Pressable
                accessibilityRole="button"
                disabled={isLoading}
                onPress={scanImage}
                style={({ pressed }) => [styles.retryButton, pressed && styles.pressed]}>
                <ThemedText type="smallBold" style={styles.retryButtonText}>
                  Retry scan
                </ThemedText>
              </Pressable>
            )}
          </View>
        )}

        {scanResult && (
          <ThemedView style={[styles.resultCard, { borderColor: theme.backgroundSelected }]}>
            <ThemedText type="smallBold" style={styles.resultLabel}>
              TOP MATCH
            </ThemedText>
            <View style={styles.resultHeading}>
              <ThemedText type="subtitle" style={styles.resultName}>
                {scanResult.top_prediction.label}
              </ThemedText>
              <View style={styles.confidenceBadge}>
                <ThemedText type="smallBold" style={styles.confidenceText}>
                  {formatConfidence(scanResult.top_prediction.score)}
                </ThemedText>
              </View>
            </View>

            <ThemedText type="small" themeColor="textSecondary">
              Disposal guidance has not yet been checked against local rules.
            </ThemedText>

            {scanResult.alternatives.length > 0 && (
              <View style={styles.alternatives}>
                <ThemedText type="smallBold">Other possible matches</ThemedText>
                {scanResult.alternatives.map((prediction) => (
                  <View key={prediction.label} style={styles.alternativeRow}>
                    <ThemedText type="small" style={styles.alternativeName}>
                      {prediction.label}
                    </ThemedText>
                    <ThemedText type="smallBold" themeColor="textSecondary">
                      {formatConfidence(prediction.score)}
                    </ThemedText>
                  </View>
                ))}
              </View>
            )}
          </ThemedView>
        )}
      </SafeAreaView>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    alignItems: 'center',
    paddingTop: Platform.OS === 'web' ? 88 : 0,
    paddingBottom: BottomTabInset + Spacing.four,
  },
  safeArea: {
    width: '100%',
    maxWidth: MaxContentWidth,
    paddingHorizontal: Spacing.four,
    gap: Spacing.four,
  },
  header: {
    paddingTop: Spacing.four,
    gap: Spacing.two,
  },
  eyebrowRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  logoMark: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#168653',
  },
  eyebrow: {
    color: '#168653',
    letterSpacing: 2,
    textTransform: 'uppercase',
  },
  title: {
    fontSize: 44,
    lineHeight: 50,
  },
  subtitle: {
    maxWidth: 600,
  },
  scanCard: {
    padding: Spacing.three,
    borderRadius: Spacing.four,
    gap: Spacing.three,
  },
  preview: {
    width: '100%',
    aspectRatio: 4 / 3,
    borderRadius: Spacing.three,
    backgroundColor: '#dfe7e2',
  },
  emptyPreview: {
    width: '100%',
    aspectRatio: 4 / 3,
    maxHeight: 420,
    borderRadius: Spacing.three,
    borderWidth: 1,
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
    padding: Spacing.four,
    gap: Spacing.two,
    opacity: 0.75,
  },
  emptyIcon: {
    color: '#168653',
    fontSize: 48,
    lineHeight: 54,
  },
  centerText: {
    maxWidth: 340,
    textAlign: 'center',
  },
  actions: {
    gap: Spacing.two,
    flexDirection: Platform.OS === 'web' ? 'row' : 'column',
  },
  secondaryButton: {
    minHeight: 50,
    borderWidth: 1,
    borderRadius: Spacing.three,
    paddingHorizontal: Spacing.four,
    alignItems: 'center',
    justifyContent: 'center',
    flexGrow: 1,
  },
  primaryButton: {
    minHeight: 50,
    borderRadius: Spacing.three,
    paddingHorizontal: Spacing.four,
    backgroundColor: '#168653',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.two,
    flexGrow: 1,
  },
  primaryButtonText: {
    color: '#ffffff',
  },
  pressed: {
    opacity: 0.72,
  },
  disabled: {
    opacity: 0.65,
  },
  errorCard: {
    backgroundColor: '#ffe8e6',
    borderRadius: Spacing.three,
    borderLeftColor: '#bd2c24',
    borderLeftWidth: 4,
    padding: Spacing.three,
    gap: Spacing.one,
  },
  errorTitle: {
    color: '#8e1c17',
  },
  errorText: {
    color: '#8e1c17',
  },
  retryButton: {
    alignSelf: 'flex-start',
    minHeight: 42,
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#8e1c17',
    marginTop: Spacing.one,
  },
  retryButtonText: {
    color: '#ffffff',
  },
  resultCard: {
    borderRadius: Spacing.four,
    borderWidth: 1,
    padding: Spacing.four,
    gap: Spacing.three,
  },
  resultLabel: {
    color: '#168653',
    letterSpacing: 1.5,
  },
  resultHeading: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.three,
  },
  resultName: {
    flex: 1,
    textTransform: 'capitalize',
  },
  confidenceBadge: {
    borderRadius: Spacing.five,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    backgroundColor: '#dff7ea',
  },
  confidenceText: {
    color: '#09683b',
  },
  alternatives: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: '#aeb8b2',
    paddingTop: Spacing.three,
    gap: Spacing.two,
  },
  alternativeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.three,
  },
  alternativeName: {
    flex: 1,
    textTransform: 'capitalize',
  },
});
