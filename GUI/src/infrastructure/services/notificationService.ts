import { apiClient } from '../../config';
import type {
  AppNotification,
  NotificationSettings,
  NotificationsListResponse,
  TelegramLinkTokenResponse
} from '../../core/ports';

export const notificationService = {
  getSettings: (): Promise<NotificationSettings> => apiClient.getNotificationSettings(),
  putSettings: (
    data: Partial<{ language: string; telegramEnabled: boolean; inAppNotificationsEnabled: boolean }>
  ): Promise<NotificationSettings> => apiClient.putNotificationSettings(data),
  getNotifications: (
    page?: number,
    perPage?: number,
    status?: string,
    readState?: 'unread' | 'read'
  ): Promise<NotificationsListResponse> => apiClient.getNotifications(page, perPage, status, readState),
  getUnreadCount: (): Promise<number> =>
    apiClient.getUnreadNotificationsCount().then(r => r.count),
  markRead: (id: number): Promise<void> => apiClient.markNotificationRead(id),
  markAllRead: (): Promise<{ updated: number }> => apiClient.markAllNotificationsRead(),
  createTelegramLink: (): Promise<TelegramLinkTokenResponse> => apiClient.createTelegramLinkToken(),
  unlinkTelegram: (): Promise<void> => apiClient.deleteTelegramLink()
};

export type { AppNotification, NotificationSettings };
