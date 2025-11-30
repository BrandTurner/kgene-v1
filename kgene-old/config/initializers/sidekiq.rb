Rails.application.configure do
  config.active_job.queue_adapter = :sidekiq
end
#
# Sidekiq.configure_server do |config|
#   config.redis = { url: 'redis://localhost:6379' }
# end
#
# Sidekiq.configure_client do |config|
#   config.redis = { url: 'redis://localhost:6379' }
# end