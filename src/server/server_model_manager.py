"""
Authors: Prince Modi, Roopkatha Banerjee, Yogesh Simmhan
Emails: princemodi@iisc.ac.in, roopkathab@iisc.ac.in, simmhan@iisc.ac.in
Copyright 2023 Indian Institute of Science
Licensed under the Apache License, Version 2.0, http://www.apache.org/licenses/LICENSE-2.0
"""

import torch
from tqdm import tqdm

from server.load_loss import load_loss
from server.load_optimizer import load_optimizer
from server.server_file_manager import get_model_class
from utils.logger import FedLogger


class ServerModelManager:
    def __init__(
        self,
        id,
        model_dir,
        model_class,
        batch_size,
        val_data_path,
        torch_device=torch.device("cpu"),
        model_args: dict = None,
        use_custom_dataloader=False,
        custom_dataloader_args: dict = None,
        use_custom_validator=False,
        custom_validator_args=None,
    ) -> None:
        self.id = id
        self.torch_device = torch_device
        self.model_dir = model_dir

        torch.manual_seed(1122001)
        model_cls = get_model_class(path=model_dir, class_name=model_class)
        if model_cls is None:
            raise ValueError(f"Could not load model class '{model_class}' from '{model_dir}'. Please check logs for import errors.")
            
        self.model = model_cls(
            device=torch_device, args=model_args
        )

        self.logger = FedLogger(id=self.id, loggername="SERVER_MODEL_MANAGER")

        if use_custom_dataloader:
            DataLoader = get_model_class(
                path=model_dir, class_name="CustomDataLoader"
            )()
            _, self.data = DataLoader.get_train_test_dataset_loaders(
                batch_size=batch_size,
                dataset_path=val_data_path,
                args=custom_dataloader_args,
            )
        else:
            self.data = self.test_dataset_loader(
                path=val_data_path, batch_size=batch_size
            )

        self.use_custom_validator = use_custom_validator
        self.custom_validator_args = custom_validator_args

    def get_model_weights(self):
        self.model.to("cpu")
        return self.model.state_dict()

    def set_model_weights(self, model_weights):
        self.model.load_state_dict(model_weights)

    def get_model_params(self):
        return sum(p.numel() for p in self.model.parameters() if p.requires_grad)

    def get_optimizer(self):
        return self.optimizer

    # TODO add check if None
    def set_optimizer(self, lr, optimizer, custom):
        opt = load_optimizer(self.id, optimizer, custom)
        self.optimizer = opt.optimizer_selection(self.model.parameters(), lr=lr)

    # TODO add check if None
    def set_loss_fun(self, loss_fun, custom):
        loss = load_loss(self.id, loss_fun, custom)
        self.loss_fun = loss.loss_function_selection()

    def get_loss_fun(self):
        return self.loss_fun

    def test_dataset_loader(self, path: str, batch_size=50):
        print(f"[DEBUG] test_dataset_loader: Loading validation data from: {path}")
        try:
            loaded_obj = torch.load(path, weights_only=False)
            print(f"[DEBUG] test_dataset_loader: Loaded object type: {type(loaded_obj)}")
            
            if hasattr(loaded_obj, 'dataset'):
                test_dataset = loaded_obj.dataset
                print(f"[DEBUG] test_dataset_loader: Using .dataset attribute")
            else:
                test_dataset = loaded_obj
                print(f"[DEBUG] test_dataset_loader: Using loaded object directly")
            
            print(f"[DEBUG] test_dataset_loader: Dataset type: {type(test_dataset)}")
            print(f"[DEBUG] test_dataset_loader: Length of test dataset: {len(test_dataset)}")
            
            # Check model's expected input channels
            model_expects_grayscale = False
            try:
                # Check if model has a conv layer that expects 1 channel input
                if hasattr(self.model, 'feature_extractor'):
                    first_layer = self.model.feature_extractor[0]
                    if hasattr(first_layer, 'in_channels') and first_layer.in_channels == 1:
                        model_expects_grayscale = True
                elif hasattr(self.model, 'conv1'):
                    if hasattr(self.model.conv1, 'in_channels') and self.model.conv1.in_channels == 1:
                        model_expects_grayscale = True
                print(f"[DEBUG] test_dataset_loader: Model expects grayscale: {model_expects_grayscale}")
            except Exception as e:
                print(f"[DEBUG] test_dataset_loader: Could not determine model input channels: {e}")
            
            # Check first sample to see if we need grayscale conversion
            sample_img, _ = test_dataset[0]
            if hasattr(sample_img, 'shape'):
                print(f"[DEBUG] test_dataset_loader: First sample shape: {sample_img.shape}")
                # Only convert if image has 3 channels BUT model expects 1 channel
                if len(sample_img.shape) == 3 and sample_img.shape[0] == 3 and model_expects_grayscale:
                    print(f"[DEBUG] test_dataset_loader: Detected 3-channel images but model expects 1-channel, will convert to grayscale")
                    
                    # Wrap dataset to convert RGB to grayscale
                    class GrayscaleDataset(torch.utils.data.Dataset):
                        def __init__(self, dataset):
                            self.dataset = dataset
                            
                        def __getitem__(self, idx):
                            img, label = self.dataset[idx]
                            # Convert RGB to grayscale by taking mean across channels
                            if len(img.shape) == 3 and img.shape[0] == 3:
                                img = img.mean(dim=0, keepdim=True)
                            return img, label
                        
                        def __len__(self):
                            return len(self.dataset)
                    
                    test_dataset = GrayscaleDataset(test_dataset)
                    print(f"[DEBUG] test_dataset_loader: Wrapped dataset with grayscale converter")
                else:
                    print(f"[DEBUG] test_dataset_loader: No conversion needed - data has {sample_img.shape[0] if len(sample_img.shape) == 3 else 1} channels, model expects {'1' if model_expects_grayscale else '3'} channels")


            data = torch.utils.data.DataLoader(
                dataset=test_dataset, batch_size=batch_size, shuffle=True
            )
            print(f"[DEBUG] test_dataset_loader: DataLoader created with {len(data)} batches")
            return data
        except Exception as e:
            print(f"[ERROR] test_dataset_loader: Failed to load validation data: {e}")
            import traceback
            traceback.print_exc()
            raise

    def validate_model(
        self,
        device: str = "cpu",
        loss_func=None,
        optimizer=None,
        round_no=None,
    ):
        if self.use_custom_validator:
            validator = get_model_class(
                path=self.model_dir, class_name="CustomModelTrainer"
            )
            res = validator.validate_model(
                self,
                model=self.model,
                dataloader=self.data,
                device=device,
                loss_func=loss_func,
                optimizer=optimizer,
                round_no=round_no,
                args=self.custom_validator_args,
            )

        else:
            print(f"[DEBUG] Starting server-side validation for round {round_no}")
            try:
                self.model = self.model.to(self.torch_device)
                self.model.eval()
                print(f"[DEBUG] Model moved to {self.torch_device} and set to eval mode")

                acc = 0
                count = 0
                total_loss = 0
                batches = 0
                
                print(f"[DEBUG] Starting validation loop over {len(self.data)} batches")
                with torch.no_grad():
                    cost = self.loss_fun()
                    for i, (x_batch, y_batch) in tqdm(
                        enumerate(self.data), total=len(self.data), desc="Validation Round"
                    ):
                        if i == 0:
                            print(f"[DEBUG] First batch - x_batch shape: {x_batch.shape}, y_batch shape: {y_batch.shape}")
                        
                        x_batch = x_batch.to(self.torch_device)
                        y_batch = y_batch.to(self.torch_device)
                        
                        if i == 0:
                            print(f"[DEBUG] Running forward pass on first batch...")
                        y_pred = self.model(x_batch)
                        
                        if i == 0:
                            print(f"[DEBUG] First batch prediction shape: {y_pred.shape}")
                        
                        loss = cost(y_pred, y_batch)
                        total_loss += loss.item()
                        acc += (torch.argmax(y_pred, 1) == y_batch).float().sum().item()
                        count += len(y_batch)
                        batches = i + 1

                print(f"[DEBUG] Validation loop completed. Processed {batches} batches, {count} samples")
                acc = (acc / count) * 100
                loss = total_loss / batches

                self.model.train()
                res = {"accuracy": acc, "loss": loss}
                print(f"[VALIDATION RESULTS] Round {round_no}: Accuracy={acc:.2f}%, Loss={loss:.4f}")
                print(res)
            except Exception as e:
                print(f"[ERROR] Validation failed: {e}")
                import traceback
                traceback.print_exc()
                raise

        return res
