class CreateOrganisms < ActiveRecord::Migration
  def change
    create_table :organisms do |t|
      t.string :code, :name
      t.timestamps null: false
    end
  end
end
