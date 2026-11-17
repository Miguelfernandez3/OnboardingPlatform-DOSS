import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../infrastructure/query/queryKeys';
import { notificationService, type NotificationSettings } from '../../infrastructure/services/notificationService';

/**
 * Ajustes de notificación del usuario (app / Telegram) y acciones de enlace.
 */
export function useNotificationSettings() {
  const queryClient = useQueryClient();

  const settingsQuery = useQuery({
    queryKey: queryKeys.settings.notification,
    queryFn: () => notificationService.getSettings(),
    staleTime: 60_000
  });

  const putSettingsMutation = useMutation({
    mutationFn: (patch: Partial<Pick<NotificationSettings, 'telegramEnabled' | 'inAppNotificationsEnabled'>>) =>
      notificationService.putSettings(patch),
    onSuccess: (next) => {
      queryClient.setQueryData(queryKeys.settings.notification, next);
    }
  });

  const createTelegramLinkMutation = useMutation({
    mutationFn: () => notificationService.createTelegramLink()
  });

  const unlinkTelegramMutation = useMutation({
    mutationFn: () => notificationService.unlinkTelegram(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings.notification });
    }
  });

  return {
    settingsQuery,
    putSettingsMutation,
    createTelegramLinkMutation,
    unlinkTelegramMutation,
    settings: settingsQuery.data ?? null,
    isLoading: settingsQuery.isLoading,
    isError: settingsQuery.isError,
    error: settingsQuery.error
  };
}
