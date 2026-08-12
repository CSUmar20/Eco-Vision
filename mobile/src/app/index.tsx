import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { type Href, useRouter } from 'expo-router';
import { SymbolView } from 'expo-symbols';
import { useRef, useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { classifyImage, confirmScan, type ScanResult } from '@/api/classify';
import { HomeDock } from '@/components/home-dock';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

function formatConfidence(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export default function HomeScreen() {
  const router = useRouter();
  const scrollViewRef = useRef<ScrollView>(null);
  const theme = useTheme();
  const [selectedImage, setSelectedImage] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [confirmedLabel, setConfirmedLabel] = useState<string | null>(null);
  const [confirmationError, setConfirmationError] = useState<string | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);

  function resetResultState() {
    setScanResult(null);
    setErrorMessage(null);
    setConfirmedLabel(null);
    setConfirmationError(null);
  }

  async function analyzeAsset(asset: ImagePicker.ImagePickerAsset) {
    if (isLoading) {
      return;
    }

    setSelectedImage(asset);
    resetResultState();
    setIsLoading(true);

    try {
      const result = await classifyImage(asset);
      setScanResult(result);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'The image could not be scanned.');
    } finally {
      setIsLoading(false);
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

      if (!result.canceled && result.assets[0]) {
        await analyzeAsset(result.assets[0]);
      }
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

      if (!result.canceled && result.assets[0]) {
        await analyzeAsset(result.assets[0]);
      }
    } catch {
      setErrorMessage('The camera could not be opened. Please try again.');
    }
  }

  async function retryScan() {
    if (selectedImage) {
      await analyzeAsset(selectedImage);
    }
  }

  function returnHome() {
    setSelectedImage(null);
    resetResultState();
    scrollViewRef.current?.scrollTo({ y: 0, animated: true });
  }

  async function confirmPrediction(label: string) {
    if (!scanResult || isConfirming) {
      return;
    }

    setIsConfirming(true);
    setConfirmationError(null);

    try {
      const confirmation = await confirmScan(scanResult.scan_id, label);
      setConfirmedLabel(confirmation.confirmed_label);
    } catch (error) {
      setConfirmationError(
        error instanceof Error ? error.message : 'The confirmation could not be saved.',
      );
    } finally {
      setIsConfirming(false);
    }
  }

  return (
    <View style={[styles.screen, { backgroundColor: theme.background }]}>
      <ScrollView
        ref={scrollViewRef}
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}>
        <SafeAreaView style={styles.safeArea} edges={['top', 'left', 'right']}>
          <View style={styles.topBar}>
            <View style={styles.brandRow}>
              <View style={styles.brandMark} />
              <ThemedText type="smallBold" style={styles.brandText}>
                ECOVISION
              </ThemedText>
            </View>

            <Pressable
              accessibilityLabel="Open settings"
              accessibilityRole="button"
              onPress={() => router.push('/settings' as Href)}
              style={({ pressed }) => [
                styles.settingsButton,
                { backgroundColor: theme.backgroundElement },
                pressed && styles.pressed,
              ]}>
              <SymbolView
                name={{ ios: 'gearshape.fill', android: 'settings', web: 'settings' }}
                size={24}
                tintColor={theme.text}
              />
            </Pressable>
          </View>

          <View style={styles.hero}>
            <View style={styles.heroCopy}>
              <ThemedText type="title" style={styles.heroTitle}>
                Tap to recycle
              </ThemedText>
              <ThemedText themeColor="textSecondary" style={styles.heroSubtitle}>
                Photograph one item. EcoVision will identify its closest material match.
              </ThemedText>
            </View>

            <Pressable
              accessibilityHint="Opens the camera to identify a recyclable item"
              accessibilityLabel="Tap to recycle"
              accessibilityRole="button"
              disabled={isLoading}
              onPress={takePhoto}
              style={({ pressed }) => [
                styles.leafButton,
                pressed && styles.leafPressed,
                isLoading && styles.disabled,
              ]}>
              <View style={styles.leafGlow} />
              <Image
                source={require('@/assets/images/hex-leaf.svg')}
                style={styles.leafImage}
                contentFit="contain"
              />
              {isLoading && (
                <View style={styles.leafLoading}>
                  <ActivityIndicator color="#ffffff" size="large" />
                  <ThemedText type="smallBold" style={styles.leafLoadingText}>
                    Identifying…
                  </ThemedText>
                </View>
              )}
            </Pressable>

            <ThemedText type="smallBold" style={styles.cameraHint}>
              TAP THE LEAF TO OPEN CAMERA
            </ThemedText>
          </View>

          {selectedImage && (
            <ThemedView type="backgroundElement" style={styles.selectedCard}>
              <Image
                source={{ uri: selectedImage.uri }}
                style={styles.selectedPreview}
                contentFit="cover"
              />
              <View style={styles.selectedCopy}>
                <ThemedText type="smallBold">Selected item</ThemedText>
                <ThemedText type="small" themeColor="textSecondary">
                  {isLoading
                    ? 'EcoVision is comparing the image with its candidate categories.'
                    : scanResult
                      ? 'Analysis complete.'
                      : 'The item is ready to scan again.'}
                </ThemedText>
              </View>
            </ThemedView>
          )}

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
                  onPress={retryScan}
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

              <View style={styles.feedbackSection}>
                <View style={styles.feedbackHeading}>
                  <ThemedText type="smallBold">Does this match your item?</ThemedText>
                  {isConfirming && <ActivityIndicator color="#78977a" size="small" />}
                </View>

                {confirmedLabel ? (
                  <View accessibilityRole="alert" style={styles.confirmationSuccess}>
                    <ThemedText type="smallBold" style={styles.confirmationSuccessTitle}>
                      Match confirmed
                    </ThemedText>
                    <ThemedText type="small" style={styles.confirmationSuccessText}>
                      You selected “{confirmedLabel}.” Thanks for helping improve EcoVision.
                    </ThemedText>
                  </View>
                ) : (
                  <>
                    <Pressable
                      accessibilityRole="button"
                      disabled={isConfirming}
                      onPress={() => confirmPrediction(scanResult.top_prediction.label)}
                      style={({ pressed }) => [
                        styles.confirmButton,
                        pressed && styles.pressed,
                        isConfirming && styles.disabled,
                      ]}>
                      <ThemedText type="smallBold" style={styles.confirmButtonText}>
                        Yes, this is correct
                      </ThemedText>
                    </Pressable>

                    {scanResult.alternatives.length > 0 && (
                      <View style={styles.correctionOptions}>
                        <ThemedText type="small" themeColor="textSecondary">
                          If not, choose the closest match:
                        </ThemedText>
                        {scanResult.alternatives.map((prediction) => (
                          <Pressable
                            accessibilityRole="button"
                            disabled={isConfirming}
                            key={`confirmation-${prediction.label}`}
                            onPress={() => confirmPrediction(prediction.label)}
                            style={({ pressed }) => [
                              styles.correctionButton,
                              { borderColor: theme.backgroundSelected },
                              pressed && styles.pressed,
                              isConfirming && styles.disabled,
                            ]}>
                            <ThemedText type="small" style={styles.correctionLabel}>
                              {prediction.label}
                            </ThemedText>
                            <ThemedText type="smallBold" themeColor="textSecondary">
                              {formatConfidence(prediction.score)}
                            </ThemedText>
                          </Pressable>
                        ))}
                      </View>
                    )}
                  </>
                )}

                {confirmationError && (
                  <ThemedText
                    accessibilityRole="alert"
                    type="small"
                    style={styles.confirmationError}>
                    {confirmationError}
                  </ThemedText>
                )}
              </View>
            </ThemedView>
          )}
        </SafeAreaView>
      </ScrollView>

      <HomeDock
        disabled={isLoading}
        onAddPhoto={chooseImage}
        onHome={returnHome}
        onSetLocation={() => router.push('/location' as Href)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    alignItems: 'center',
    paddingBottom: 132,
  },
  safeArea: {
    width: '100%',
    maxWidth: MaxContentWidth,
    paddingHorizontal: Spacing.four,
    gap: Spacing.four,
  },
  topBar: {
    paddingTop: Spacing.two,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  brandMark: {
    width: 12,
    height: 12,
    borderRadius: 2,
    backgroundColor: '#78977a',
    transform: [{ rotate: '45deg' }],
  },
  brandText: {
    color: '#52735b',
    letterSpacing: 2,
  },
  settingsButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  hero: {
    minHeight: Platform.OS === 'web' ? 570 : 525,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.three,
  },
  heroCopy: {
    alignItems: 'center',
    gap: Spacing.two,
  },
  heroTitle: {
    fontSize: 42,
    lineHeight: 48,
    textAlign: 'center',
  },
  heroSubtitle: {
    maxWidth: 430,
    textAlign: 'center',
  },
  leafButton: {
    width: 276,
    height: 310,
    alignItems: 'center',
    justifyContent: 'center',
  },
  leafGlow: {
    position: 'absolute',
    width: 208,
    height: 264,
    borderTopLeftRadius: 150,
    borderTopRightRadius: 34,
    borderBottomRightRadius: 150,
    borderBottomLeftRadius: 34,
    backgroundColor: '#dfe9da',
    opacity: 0.72,
    transform: [{ rotate: '42deg' }],
  },
  leafImage: {
    width: 260,
    height: 306,
  },
  leafPressed: {
    transform: [{ scale: 0.96 }],
  },
  leafLoading: {
    position: 'absolute',
    width: 150,
    height: 150,
    borderRadius: 75,
    backgroundColor: 'rgba(52, 92, 67, 0.92)',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.two,
  },
  leafLoadingText: {
    color: '#ffffff',
  },
  cameraHint: {
    color: '#52735b',
    fontSize: 11,
    letterSpacing: 1.4,
  },
  selectedCard: {
    padding: Spacing.three,
    borderRadius: Spacing.four,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
  },
  selectedPreview: {
    width: 84,
    height: 84,
    borderRadius: Spacing.three,
    backgroundColor: '#dfe9da',
  },
  selectedCopy: {
    flex: 1,
    gap: Spacing.one,
  },
  pressed: {
    opacity: 0.72,
  },
  disabled: {
    opacity: 0.62,
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
    color: '#52735b',
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
    backgroundColor: '#dfe9da',
  },
  confidenceText: {
    color: '#345c43',
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
  feedbackSection: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: '#aeb8b2',
    paddingTop: Spacing.three,
    gap: Spacing.two,
  },
  feedbackHeading: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.two,
  },
  confirmButton: {
    minHeight: 48,
    borderRadius: Spacing.three,
    paddingHorizontal: Spacing.four,
    backgroundColor: '#78977a',
    alignItems: 'center',
    justifyContent: 'center',
  },
  confirmButtonText: {
    color: '#ffffff',
  },
  correctionOptions: {
    gap: Spacing.two,
  },
  correctionButton: {
    minHeight: 46,
    borderWidth: 1,
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.three,
  },
  correctionLabel: {
    flex: 1,
    textTransform: 'capitalize',
  },
  confirmationSuccess: {
    borderRadius: Spacing.two,
    padding: Spacing.three,
    backgroundColor: '#dfe9da',
    gap: Spacing.one,
  },
  confirmationSuccessTitle: {
    color: '#345c43',
  },
  confirmationSuccessText: {
    color: '#345c43',
  },
  confirmationError: {
    color: '#8e1c17',
  },
});
