import React from 'react';
import { View, Text, TouchableOpacity, ScrollView, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, typography, radius, spacing } from '../theme/theme';

interface ChatHomeProps {
  onQuickAction: (action: string) => void;
}

export function ChatHome({ onQuickAction }: ChatHomeProps) {
  const hour = new Date().getHours();
  let greeting = 'Good morning,';
  if (hour >= 12 && hour < 17) greeting = 'Good afternoon,';
  else if (hour >= 17) greeting = 'Good evening,';

  return (
    <View style={styles.container}>
      <Text style={styles.greeting}>{greeting}</Text>
      <Text style={styles.brandTitle}>
        I'm <Text style={styles.brandHighlight}>Blinky.</Text>
      </Text>
      
      <Text style={styles.subtitle}>
        Control your PC, just a message away.
      </Text>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.actionsRow}>
        <TouchableOpacity style={styles.actionBtn} onPress={() => onQuickAction('Open app')} activeOpacity={0.7}>
          <Ionicons name="play-circle-outline" size={18} color={colors.textPrimary} style={styles.actionIcon} />
          <Text style={styles.actionText}>Open app</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.actionBtn} onPress={() => onQuickAction('Run command')} activeOpacity={0.7}>
          <Ionicons name="terminal-outline" size={18} color={colors.textPrimary} style={styles.actionIcon} />
          <Text style={styles.actionText}>Run command</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.actionBtn} onPress={() => onQuickAction('Screenshot')} activeOpacity={0.7}>
          <Ionicons name="scan-outline" size={18} color={colors.textPrimary} style={styles.actionIcon} />
          <Text style={styles.actionText}>Screenshot</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xxl,
    paddingBottom: spacing.xl,
  },
  greeting: {
    ...typography.heading2,
    color: colors.textSecondary,
    fontWeight: '500',
  },
  brandTitle: {
    ...typography.heading1,
    color: colors.textPrimary,
    fontSize: 40,
    marginTop: 4,
    marginBottom: spacing.md,
  },
  brandHighlight: {
    color: colors.accent,
  },
  subtitle: {
    ...typography.bodyLarge,
    color: colors.textSecondary,
    marginBottom: spacing.xl,
  },
  actionsRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  actionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surfaceElevated,
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  actionIcon: {
    marginRight: 6,
  },
  actionText: {
    ...typography.bodySmall,
    color: colors.textPrimary,
    fontWeight: '500',
  },
});
